/**
 * 智慧学伴 校验工具
 */

/**
 * 校验邮箱格式
 * @param email 邮箱地址
 * @returns 是否有效
 */
export function isValidEmail(email: string): boolean {
  const pattern = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/
  return pattern.test(email)
}

/**
 * 校验手机号格式（中国大陆）
 * @param phone 手机号
 * @returns 是否有效
 */
export function isValidPhone(phone: string): boolean {
  const pattern = /^1[3-9]\d{9}$/
  return pattern.test(phone)
}

/**
 * 校验密码强度
 * 要求：至少6位，包含字母和数字
 * @param password 密码
 * @returns 校验结果
 */
export function validatePassword(password: string): { valid: boolean; message: string } {
  if (password.length < 6) {
    return { valid: false, message: '密码长度至少6位' }
  }
  if (password.length > 50) {
    return { valid: false, message: '密码长度不能超过50位' }
  }
  if (!/[a-zA-Z]/.test(password)) {
    return { valid: false, message: '密码必须包含字母' }
  }
  if (!/\d/.test(password)) {
    return { valid: false, message: '密码必须包含数字' }
  }
  return { valid: true, message: '' }
}

/**
 * 校验昵称
 * @param nickname 昵称
 * @returns 校验结果
 */
export function validateNickname(nickname: string): { valid: boolean; message: string } {
  if (nickname.length < 2) {
    return { valid: false, message: '昵称至少2个字符' }
  }
  if (nickname.length > 50) {
    return { valid: false, message: '昵称不能超过50个字符' }
  }
  return { valid: true, message: '' }
}

/**
 * 校验场景类型
 * @param sceneType 场景类型
 * @returns 是否有效
 */
export function isValidSceneType(sceneType: string): boolean {
  const validTypes = ['classroom', 'self_study', 'exam', 'discussion']
  return validTypes.includes(sceneType)
}

/**
 * 校验URL格式
 * @param url URL字符串
 * @returns 是否有效
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}
