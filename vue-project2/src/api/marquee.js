import { api, unwrap } from '@/api/client'

/** 首页跑马灯（公开接口） */
export async function fetchHomeMarquee() {
  return unwrap(await api.get('/api/home/marquee'))
}
