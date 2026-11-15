@echo off
:: 智慧学伴 远程访问隧道启动脚本
:: 使用 Cloudflare Quick Tunnel（免费，无需注册）
:: 将本机 localhost:5173（前端+API代理）暴露到公网

echo ========================================
echo   智慧学伴 远程访问隧道
echo ========================================
echo.

set CF=C:\Users\chenanguo\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe

echo [*] 启动前端隧道 (localhost:5173)...
echo [*] 前端包含 Vite proxy，自动代理后端 API
echo [*] 隧道建立后，将显示公网 URL，发给队友即可
echo.
echo   队友使用流程:
echo   1. 在浏览器打开隧道 URL
echo   2. 点击"注册"创建账号（邮箱+密码+昵称+角色）
echo   3. 注册后自动登录
echo.
echo   管理员账号: admin@ai4edu.com / admin123
echo.
echo [!] 注意: 关闭此窗口将断开隧道
echo ========================================
echo.

"%CF%" tunnel --url http://localhost:5173

pause
