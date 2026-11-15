#!/usr/bin/env python3
"""Complete v2 deployment to Alibaba Cloud ECS with Alibaba Cloud mirrors."""
import paramiko
import time
import sys
import os
import socket

HOST = '121.43.129.181'
USER = 'root'
PASSWORD = 'Team_Shin@2026'
LOCAL_DOCKERFILE = os.path.join(os.path.dirname(__file__), '..', 'backend', 'Dockerfile')
REMOTE_DOCKERFILE = '/opt/ai4edu/backend/Dockerfile'

def run_cmd(client, cmd, timeout=300, stream=True):
    """Execute a command via SSH and return output."""
    print(f'\n{"="*60}')
    print(f'>>> {cmd[:100]}')
    print(f'{"="*60}')
    chan = client.get_transport().open_session()
    chan.get_pty()
    chan.exec_command(cmd)
    chan.settimeout(timeout)
    output = ''
    start_time = time.time()
    try:
        while True:
            try:
                data = chan.recv(4096).decode(errors='ignore')
                if not data:
                    break
                output += data
                if stream:
                    print(data, end='', flush=True)
            except socket.timeout:
                elapsed = time.time() - start_time
                print(f'\n[Timeout after {elapsed:.0f}s]')
                break
    except Exception as e:
        print(f'\n[Error: {e}]')
    ret = chan.recv_exit_status()
    print(f'\n[Exit code: {ret}]')
    return ret, output

def upload_file(client, local_path, remote_path):
    """Upload a file via SFTP."""
    sftp = client.open_sftp()
    try:
        sftp.put(local_path, remote_path)
        print(f'Uploaded: {local_path} -> {remote_path}')
    finally:
        sftp.close()

def main():
    print('=== 智慧学伴 v2 Cloud Deployment (Alibaba Cloud Mirrors) ===')

    # 1. Connect
    print('\n[1/8] Connecting to server...')
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print('Connected.')

    try:
        # 2. Upload modified Dockerfile
        print('\n[2/8] Uploading modified Dockerfile (with Alibaba Cloud mirrors)...')
        upload_file(client, LOCAL_DOCKERFILE, REMOTE_DOCKERFILE)
        # Verify
        ret, _ = run_cmd(client, f'cat {REMOTE_DOCKERFILE} | head -10', timeout=10)

        # 3. Kill any running docker build processes
        print('\n[3/8] Cleaning up any stuck Docker builds...')
        run_cmd(client, 'docker builder prune -f 2>/dev/null; pkill -f "docker.*build" 2>/dev/null; true', timeout=30)

        # 4. Build new backend image with Alibaba Cloud mirrors
        print('\n[4/8] Building backend image (should be much faster with aliyun mirrors)...')
        ret, build_output = run_cmd(client,
            'cd /opt/ai4edu && docker compose -f deploy/docker-compose.yml build backend --no-cache 2>&1',
            timeout=600)
        if ret != 0:
            print('BUILD FAILED! Checking last 50 lines...')
            print(build_output[-3000:] if build_output else 'No output')
            return

        # 5. Recreate backend container
        print('\n[5/8] Recreating backend container...')
        ret, _ = run_cmd(client,
            'cd /opt/ai4edu && docker compose -f deploy/docker-compose.yml up -d --force-recreate backend 2>&1',
            timeout=120)
        time.sleep(8)

        # 6. Check backend logs
        print('\n[6/8] Checking backend startup logs...')
        ret, logs = run_cmd(client, 'docker logs ai4edu-backend --tail 30 2>&1', timeout=30)

        # 7. Alembic migration: stamp current version then upgrade
        print('\n[7/8] Running Alembic migration (stamp + upgrade)...')

        # Check if alembic_version table exists and has a version
        ret, alembic_check = run_cmd(client,
            'docker exec ai4edu-postgres psql -U ai4edu -d ai4edu -c "SELECT version_num FROM alembic_version;" 2>&1',
            timeout=30)
        has_version = ret == 0 and any(line.strip() for line in alembic_check.splitlines() if line.strip() and not line.startswith('ERROR') and not line.startswith('SELECT') and not line.startswith('('))

        if not has_version:
            print('alembic_version table missing or empty. Stamping to 61a4199a88b0 (initial tables already exist)...')
            ret, stamp_out = run_cmd(client,
                'docker exec ai4edu-backend alembic stamp 61a4199a88b0 2>&1', timeout=30)
            print(f'Stamp exit code: {ret}')
            if ret != 0:
                print('Stamp failed, output:')
                print(stamp_out[-2000:])
        else:
            print(f'Alembic version already present: {alembic_check.strip()}')

        # Now upgrade to head (will run teacher_methods + v2_models migrations)
        print('Upgrading alembic to head...')
        ret, upgrade_out = run_cmd(client,
            'docker exec ai4edu-backend alembic upgrade head 2>&1', timeout=60)
        print(f'Upgrade exit code: {ret}')
        if ret != 0:
            print('Upgrade failed, output:')
            print(upgrade_out[-2000:])

        # Verify alembic version
        ret, final_version = run_cmd(client,
            'docker exec ai4edu-backend alembic current 2>&1', timeout=30)
        print(f'Final alembic version: {final_version.strip()}')

        # 8. Recreate celery containers + verify
        print('\n[8/8] Recreating celery containers and verifying...')
        # Check if celery-worker and celery-beat are defined
        run_cmd(client,
            'cd /opt/ai4edu && docker compose -f deploy/docker-compose.yml up -d --force-recreate celery-worker celery-beat 2>&1',
            timeout=120)

        time.sleep(5)

        # Check all containers
        print('\n--- Container Status ---')
        run_cmd(client, 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1', timeout=30)

        # Check v2 API endpoints
        print('\n--- API Health Check ---')
        run_cmd(client, 'curl -s http://localhost:8000/health 2>&1 || echo "health endpoint not available"', timeout=15)
        run_cmd(client, 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>&1', timeout=15)

        # Check v2 files exist in container
        print('\n--- V2 Files in Container ---')
        run_cmd(client, 'docker exec ai4edu-backend ls -la /app/app/services/ocr_service.py /app/app/services/asr_service.py /app/app/services/quota_manager.py /app/app/services/agent_export_service.py 2>&1', timeout=15)
        run_cmd(client, 'docker exec ai4edu-backend ls -la /app/app/tasks/ 2>&1', timeout=15)
        run_cmd(client, 'docker exec ai4edu-backend ls -la /app/migrations/versions/ 2>&1', timeout=15)

        # Check v2 database tables
        print('\n--- V2 Database Tables ---')
        run_cmd(client,
            'docker exec ai4edu-postgres psql -U ai4edu -d ai4edu -c "\\dt" 2>&1 | grep -E "llm_usage_logs|tenant_quotas|agent_exports|teacher_methods|classroom_records"',
            timeout=15)

        # Check celery worker registered tasks
        print('\n--- Celery Worker Status ---')
        run_cmd(client, 'docker logs ai4edu-celery-worker --tail 10 2>&1', timeout=15)

        # Check celery beat status
        print('\n--- Celery Beat Status ---')
        run_cmd(client, 'docker logs ai4edu-celery-beat --tail 10 2>&1', timeout=15)

        # Check pip packages
        print('\n--- V2 Python Packages ---')
        run_cmd(client, 'docker exec ai4edu-backend pip list 2>&1 | grep -iE "reportlab|celery|redis|paramiko"', timeout=15)

        print('\n=== DEPLOYMENT COMPLETE ===')
        print('Check the outputs above for any issues.')

    finally:
        client.close()

if __name__ == '__main__':
    main()
