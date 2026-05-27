/**
 * 将 ISO 时间转为「yyyy年MM月dd日HH时mm分」（浏览器本地时区）。
 */
export function formatOrderDateTime(isoStr) {
  if (isoStr == null || isoStr === '') return ''
  const d = new Date(isoStr)
  if (Number.isNaN(d.getTime())) return String(isoStr)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}年${m}月${day}日${h}时${min}分`
}

/**
 * 距租赁期结束的剩余时间（按整小时计，未满 1 小时不计入小时数）。
 * @returns 如「剩余时间:3天5小时」；无结束时间返回空字符串
 */
export function formatRentalRemaining(endIso) {
  if (endIso == null || endIso === '') return ''
  const end = new Date(endIso).getTime()
  if (Number.isNaN(end)) return ''
  const now = Date.now()
  const ms = end - now
  if (ms <= 0) return '剩余时间:0天0小时'
  const days = Math.floor(ms / 86400000)
  const hours = Math.floor((ms % 86400000) / 3600000)
  if (days === 0 && hours === 0) return '剩余时间:不足1小时'
  return `剩余时间:${days}天${hours}小时`
}

/** 已超期时长（按秒，与后端 overdue_seconds 一致），如「3天5小时」 */
export function formatOverdueFromSeconds(sec) {
  if (sec == null || sec <= 0) return ''
  const s = Math.floor(Number(sec))
  const days = Math.floor(s / 86400)
  const hours = Math.floor((s % 86400) / 3600)
  if (days === 0 && hours === 0) return '不足1小时'
  return `${days}天${hours}小时`
}
