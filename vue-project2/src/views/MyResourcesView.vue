<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import {
  createMyProduct,
  deleteMyProduct,
  effectiveListingType,
  listMyProducts,
  onShelfMyProduct,
  takeDownMyProduct,
  updateMyProduct,
  withdrawMyProduct,
} from '@/api/products'
import ImageLightbox from '@/components/ImageLightbox.vue'

/** 与后端 Equipment 状态一致：订单中或已售出不可编辑 */
const FROZEN_STATUSES = new Set(['待交付', '待取货', '租赁中', '已卖出'])

function canEditResource(r) {
  return !FROZEN_STATUSES.has(r.status)
}
function canOffShelfResource(r) {
  return r.status === '已上架'
}
function canOnShelfResource(r) {
  return r.status === '已下架' || r.status === '已驳回' || r.status === '已撤回'
}
function canWithdrawResource(r) {
  return r.status === '待审核'
}
function canDeleteResource(r) {
  return r.status === '已下架' || r.status === '已卖出' || r.status === '已驳回' || r.status === '已撤回'
}

const myResources = ref([])
const loading = ref(false)

/** 全部 | 出租 | 出售 */
const rentSellFilter = ref('all')

const filteredMyResources = computed(() => {
  const list = myResources.value
  if (rentSellFilter.value === 'all') return list
  return list.filter((r) => r.rentSell === rentSellFilter.value)
})

const rentSellTabCounts = computed(() => ({
  all: myResources.value.length,
  出租: myResources.value.filter((r) => r.rentSell === '出租').length,
  出售: myResources.value.filter((r) => r.rentSell === '出售').length,
}))

const detailOpen = ref(false)
const detailResource = ref(null)
const imageLightboxOpen = ref(false)
const imageLightboxSrc = ref('')
const imageLightboxAlt = ref('')

const detailIsSale = computed(() => {
  const raw = detailResource.value?.raw
  if (!raw) return false
  return effectiveListingType(raw) === 'sale'
})

function openView(r) {
  detailResource.value = r
  detailOpen.value = true
}

function closeView() {
  detailOpen.value = false
  detailResource.value = null
}

function openDetailCoverLightbox() {
  const url = detailResource.value?.raw?.cover_img_url
  if (!url) return
  imageLightboxSrc.value = url
  imageLightboxAlt.value = detailResource.value?.title || '商品封面'
  imageLightboxOpen.value = true
}
const creating = ref(false)
const editingId = ref(null)
const editing = ref(false)
const editFormEl = ref(null)
const editFirstInputEl = ref(null)

const form = reactive({
  type: '相机', // -> Django title（商品类型）
  rentSell: '出租', // -> Django category（租售）
  brand: '',
  model: '',
  description: '',
  price: '',
  deposit: '',
  location: '',
})
const coverFile = ref(null)

function onCoverChange(e) {
  const f = e?.target?.files?.[0] || null
  coverFile.value = f
}

const editForm = reactive({
  type: '相机',
  rentSell: '出租',
  brand: '',
  model: '',
  description: '',
  price: '',
  deposit: '',
  location: '',
})
const editCoverFile = ref(null)

function onEditCoverChange(e) {
  const f = e?.target?.files?.[0] || null
  editCoverFile.value = f
}

async function reload() {
  loading.value = true
  try {
    const res = await listMyProducts()
    myResources.value = res?.data || []
  } catch (e) {
    alert(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(reload)

watch(
  () => form.rentSell,
  (v) => {
    if (v === '出售') form.deposit = ''
  },
)

watch(
  () => editForm.rentSell,
  (v) => {
    if (v === '出售') editForm.deposit = ''
  },
)

async function onCreate() {
  try {
    creating.value = true
    const fd = new FormData()
    fd.append('title', form.type)
    fd.append('category', form.rentSell)
    fd.append('listing_type', form.rentSell === '出售' ? 'sale' : 'rent')
    fd.append('brand', form.brand)
    fd.append('model', form.model)
    fd.append('description', form.description)
    fd.append('price', String(form.price || '0'))
    fd.append('deposit', form.rentSell === '出售' ? '0' : String(form.deposit || '0'))
    fd.append('location', form.location)
    if (coverFile.value) fd.append('cover', coverFile.value)

    await createMyProduct(fd)
    await reload()

    // reset
    form.type = '相机'
    form.rentSell = '出租'
    form.brand = ''
    form.model = ''
    form.description = ''
    form.price = ''
    form.deposit = ''
    form.location = ''
    coverFile.value = null
  } catch (e) {
    alert(e?.message || '新增失败')
  } finally {
    creating.value = false
  }
}

async function onEdit(r) {
  if (!canEditResource(r)) {
    alert('该资源在订单流程中或已卖出，暂不可编辑')
    return
  }
  editingId.value = r.id
  const raw = r.raw || {}
  const cat = (raw.category || '').trim()
  if (cat === '出租' || cat === '出售') {
    editForm.rentSell = cat
    editForm.type = raw.title || '相机'
  } else {
    editForm.type = cat || raw.title || '相机'
    editForm.rentSell = raw.listing_type === 'sale' ? '出售' : '出租'
  }
  editForm.brand = raw.brand || ''
  editForm.model = raw.model || ''
  editForm.description = raw.description || ''
  editForm.price = raw.price || ''
  editForm.deposit = editForm.rentSell === '出售' ? '' : String(raw.deposit ?? '')
  editForm.location = raw.location || ''
  editCoverFile.value = null

  await nextTick()
  if (editFormEl.value && typeof editFormEl.value.scrollIntoView === 'function') {
    editFormEl.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  if (editFirstInputEl.value && typeof editFirstInputEl.value.focus === 'function') {
    editFirstInputEl.value.focus()
  }
}

function cancelEdit() {
  editingId.value = null
  editCoverFile.value = null
}

async function submitEdit() {
  try {
    if (!editingId.value) return
    editing.value = true
    const fd = new FormData()
    fd.append('title', editForm.type)
    fd.append('category', editForm.rentSell)
    fd.append('listing_type', editForm.rentSell === '出售' ? 'sale' : 'rent')
    fd.append('brand', editForm.brand)
    fd.append('model', editForm.model)
    fd.append('description', editForm.description)
    fd.append('price', String(editForm.price || '0'))
    fd.append('deposit', editForm.rentSell === '出售' ? '0' : String(editForm.deposit || '0'))
    fd.append('location', editForm.location)
    if (editCoverFile.value) fd.append('cover', editCoverFile.value)
    await updateMyProduct(editingId.value, fd)
    await reload()
    cancelEdit()
  } catch (e) {
    alert(e?.message || '修改失败')
  } finally {
    editing.value = false
  }
}

async function onOffShelf(r) {
  try {
    if (!canOffShelfResource(r)) {
      alert('仅「已上架」的资源可下架')
      return
    }
    if (!confirm('确定下架该资源吗？')) return
    await takeDownMyProduct(r.id)
    await reload()
  } catch (e) {
    alert(e?.message || '下架失败')
  }
}

async function onDelete(r) {
  try {
    if (!canDeleteResource(r)) {
      alert('仅「已下架」「已卖出」「已驳回」或「已撤回」的资源可删除')
      return
    }
    if (!confirm('确定永久删除该资源吗？此操作不可恢复。')) return
    await deleteMyProduct(r.id)
    await reload()
  } catch (e) {
    alert(e?.message || '删除失败')
  }
}

async function onOnShelf(r) {
  try {
    if (!canOnShelfResource(r)) {
      alert('仅已下架/已驳回/已撤回的资源可重新提交审核上架')
      return
    }
    await onShelfMyProduct(r.id)
    await reload()
  } catch (e) {
    alert(e?.message || '上架失败')
  }
}

async function onWithdraw(r) {
  try {
    if (!canWithdrawResource(r)) {
      alert('仅「待审核」的资源可撤回申请')
      return
    }
    if (!confirm('确定撤回该资源的上架申请吗？')) return
    await withdrawMyProduct(r.id)
    await reload()
  } catch (e) {
    alert(e?.message || '撤回失败')
  }
}
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">个人上架资源管理</div>
      <div class="sub">
        出租商品租期结束归还后会自动提交审核，管理员通过后再公开展示；出售商品成交后不可再上架。
      </div>
    </div>

    <div class="actions">
      <form class="createForm" @submit.prevent="onCreate">
        <div class="row">
          <div class="field">
            <label>交易类型</label>
            <select v-model="form.rentSell" :disabled="creating">
              <option value="出租">出租</option>
              <option value="出售">出售</option>
            </select>
          </div>
          <div class="field">
            <label>器材分类</label>
            <select v-model="form.type" :disabled="creating">
              <option value="相机">相机</option>
              <option value="镜头">镜头</option>
              <option value="闪光灯">闪光灯</option>
              <option value="稳定器">稳定器</option>
              <option value="三脚架">三脚架</option>
              <option value="其他">其他</option>
            </select>
          </div>
        </div>

        <div class="row">
          <div class="field">
            <label>品牌（brand）</label>
            <input v-model.trim="form.brand" :disabled="creating" placeholder="例如 Sony" />
          </div>
          <div class="field">
            <label>型号（model）</label>
            <input v-model.trim="form.model" :disabled="creating" placeholder="例如 A7M4" />
          </div>
        </div>

        <div class="row">
          <div class="field grow">
            <label>描述（description）</label>
            <input v-model.trim="form.description" :disabled="creating" placeholder="简要描述" />
          </div>
        </div>

        <div class="row">
          <div class="field">
            <label>价格（price）</label>
            <input v-model.trim="form.price" :disabled="creating" inputmode="decimal" placeholder="例如 120" />
          </div>
          <div class="field">
            <label :class="{ muted: form.rentSell === '出售' }">押金（deposit）</label>
            <input
              v-model.trim="form.deposit"
              :disabled="creating || form.rentSell === '出售'"
              inputmode="decimal"
              placeholder="例如 200"
              :title="form.rentSell === '出售' ? '出售无需填写押金' : ''"
            />
          </div>
          <div class="field">
            <label>所在地（location）</label>
            <input v-model.trim="form.location" :disabled="creating" placeholder="例如 北京" />
          </div>
        </div>

        <div class="row">
          <div class="field grow">
            <label>封面（cover）</label>
            <input
              type="file"
              accept="image/*"
              :disabled="creating"
              @change="onCoverChange"
            />
          </div>
          <button class="btn primary" type="submit" :disabled="creating">
            {{ creating ? '提交中...' : '+ 新增资源' }}
          </button>
        </div>
      </form>

      <form
        v-if="editingId"
        ref="editFormEl"
        class="createForm"
        style="margin-top: 12px;"
        @submit.prevent="submitEdit"
      >
        <div class="row">
          <div class="field grow" style="font-weight: 900;">编辑资源（ID: {{ editingId }}）</div>
        </div>

        <div class="row">
          <div class="field">
            <label>交易类型</label>
            <select v-model="editForm.rentSell" :disabled="editing">
              <option value="出租">出租</option>
              <option value="出售">出售</option>
            </select>
          </div>
          <div class="field">
            <label>器材分类</label>
            <select v-model="editForm.type" :disabled="editing">
              <option value="相机">相机</option>
              <option value="镜头">镜头</option>
              <option value="闪光灯">闪光灯</option>
              <option value="稳定器">稳定器</option>
              <option value="三脚架">三脚架</option>
              <option value="其他">其他</option>
            </select>
          </div>
        </div>

        <div class="row">
          <div class="field">
            <label>品牌（brand）</label>
            <input ref="editFirstInputEl" v-model.trim="editForm.brand" :disabled="editing" />
          </div>
          <div class="field">
            <label>型号（model）</label>
            <input v-model.trim="editForm.model" :disabled="editing" />
          </div>
        </div>

        <div class="row">
          <div class="field grow">
            <label>描述（description）</label>
            <input v-model.trim="editForm.description" :disabled="editing" />
          </div>
        </div>

        <div class="row">
          <div class="field">
            <label>价格（price）</label>
            <input v-model.trim="editForm.price" :disabled="editing" inputmode="decimal" />
          </div>
          <div class="field">
            <label :class="{ muted: editForm.rentSell === '出售' }">押金（deposit）</label>
            <input
              v-model.trim="editForm.deposit"
              :disabled="editing || editForm.rentSell === '出售'"
              inputmode="decimal"
              :title="editForm.rentSell === '出售' ? '出售无需填写押金' : ''"
            />
          </div>
          <div class="field">
            <label>所在地（location）</label>
            <input v-model.trim="editForm.location" :disabled="editing" />
          </div>
        </div>

        <div class="row">
          <div class="field grow">
            <label>更换封面（cover，可选）</label>
            <input type="file" accept="image/*" :disabled="editing" @change="onEditCoverChange" />
          </div>
          <button class="btn" type="button" :disabled="editing" @click="cancelEdit">取消</button>
          <button class="btn primary" type="submit" :disabled="editing">
            {{ editing ? '保存中...' : '保存修改' }}
          </button>
        </div>
      </form>
    </div>

    <div class="rent-sell-toolbar" role="tablist" aria-label="按租售形式筛选">
      <button
        type="button"
        class="rs-tab"
        :class="{ 'rs-tab--active': rentSellFilter === 'all' }"
        role="tab"
        :aria-selected="rentSellFilter === 'all'"
        @click="rentSellFilter = 'all'"
      >
        全部
        <span class="rs-tab__n">{{ rentSellTabCounts.all }}</span>
      </button>
      <button
        type="button"
        class="rs-tab"
        :class="{ 'rs-tab--active': rentSellFilter === '出租' }"
        role="tab"
        :aria-selected="rentSellFilter === '出租'"
        @click="rentSellFilter = '出租'"
      >
        出租
        <span class="rs-tab__n">{{ rentSellTabCounts.出租 }}</span>
      </button>
      <button
        type="button"
        class="rs-tab"
        :class="{ 'rs-tab--active': rentSellFilter === '出售' }"
        role="tab"
        :aria-selected="rentSellFilter === '出售'"
        @click="rentSellFilter = '出售'"
      >
        出售
        <span class="rs-tab__n">{{ rentSellTabCounts.出售 }}</span>
      </button>
    </div>

    <div class="table">
      <div class="tr th">
        <div>名称</div>
        <div>价格</div>
        <div>状态</div>
        <div>操作</div>
      </div>
      <div v-if="loading" class="tr"><div>加载中...</div></div>
      <div v-else-if="!filteredMyResources.length" class="tr tr--empty">
        <div>
          {{
            myResources.length
              ? '当前筛选下暂无资源，可切换「全部」或其它租售类型查看。'
              : '暂无资源，可在上方表单新增。'
          }}
        </div>
      </div>
      <template v-else>
        <div v-for="r in filteredMyResources" :key="r.id" class="tr">
          <div class="name">
            <span class="badge" :class="r.rentSell === '出售' ? 'badge--sale' : 'badge--rent'">{{ r.rentSell }}</span>
            <span class="name__text">{{ r.title }}</span>
          </div>
          <div class="money">
            ¥{{ r.pricePerDay }}<span v-if="r.rentSell === '出租'" class="money__unit">/天</span>
          </div>
          <div><span class="tag">{{ r.status }}</span></div>
          <div class="ops">
            <button class="btn" type="button" @click="openView(r)">查看</button>
            <button
              class="btn"
              type="button"
              :disabled="!canEditResource(r)"
              :title="!canEditResource(r) ? '订单进行中或已售出，不可编辑' : ''"
              @click="onEdit(r)"
            >
              编辑
            </button>
            <button v-if="canWithdrawResource(r)" class="btn" type="button" @click="onWithdraw(r)">撤回申请</button>
            <button v-if="canOffShelfResource(r)" class="btn danger" type="button" @click="onOffShelf(r)">
              下架
            </button>
            <button v-if="canOnShelfResource(r)" class="btn" type="button" @click="onOnShelf(r)">申请上架</button>
            <button v-if="canDeleteResource(r)" class="btn danger" type="button" @click="onDelete(r)">删除</button>
          </div>
        </div>
      </template>
    </div>

    <ImageLightbox v-model:open="imageLightboxOpen" :src="imageLightboxSrc" :alt="imageLightboxAlt" />

    <Teleport to="body">
      <div v-if="detailOpen" class="modal-backdrop" @click.self="closeView">
        <div class="modal panel" role="dialog" aria-modal="true">
          <div class="modal__title">资源详情</div>
          <template v-if="detailResource?.raw">
            <div v-if="detailResource.raw.cover_img_url" class="detail-cover">
              <img
                :src="detailResource.raw.cover_img_url"
                alt="封面，点击放大"
                loading="lazy"
                role="button"
                tabindex="0"
                @click="openDetailCoverLightbox"
                @keydown.enter.prevent="openDetailCoverLightbox"
                @keydown.space.prevent="openDetailCoverLightbox"
              />
            </div>
            <div class="detail-row"><span class="k">状态</span>{{ detailResource.raw.status }}</div>
            <div class="detail-row"><span class="k">浏览量</span>{{ detailResource.raw.view_count ?? 0 }}</div>
            <div class="detail-row"><span class="k">交易类型</span>{{ detailResource.rentSell }}</div>
            <div class="detail-row"><span class="k">器材分类</span>{{ detailResource.type }}</div>
            <div class="detail-row">
              <span class="k">名称</span>
              <span class="badge" :class="detailResource.rentSell === '出售' ? 'badge--sale' : 'badge--rent'">{{
                detailResource.rentSell
              }}</span>
              <span>{{ detailResource.raw.title || detailResource.title }}</span>
            </div>
            <div class="detail-row">
              <span class="k">品牌/型号</span>{{ detailResource.raw.brand }} {{ detailResource.raw.model }}
            </div>
            <div class="detail-row detail-row--block">
              <span class="k">描述</span>
              <p class="desc">{{ detailResource.raw.description || '—' }}</p>
            </div>
            <div class="detail-row detail-row--price">
              <span class="k">价格</span>
              <span class="detail-price-value">
                ¥{{ detailResource.raw.price }}<template v-if="!detailIsSale">（日租金）</template>
              </span>
            </div>
            <div class="detail-row"><span class="k">押金</span>¥{{ detailResource.raw.deposit }}</div>
            <div class="detail-row"><span class="k">位置</span>{{ detailResource.raw.location || '—' }}</div>
          </template>
          <div class="modal__actions">
            <button class="btn primary" type="button" @click="closeView">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.page {
  padding: 4px;
}
.head {
  padding: 6px 6px 14px;
}
.title {
  font-size: 18px;
  font-weight: 900;
}
.sub {
  font-size: 13px;
  opacity: 0.7;
  margin-top: 4px;
}
.actions {
  padding: 0 6px 12px;
}

.rent-sell-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 6px 12px;
}

.rs-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.45);
  color: inherit;
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
  font-weight: 800;
  font-size: 13px;
}

.rs-tab__n {
  font-size: 11px;
  font-weight: 900;
  opacity: 0.6;
  min-width: 1.1rem;
  text-align: center;
}

.rs-tab--active {
  border-color: rgba(99, 102, 241, 0.4);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.16), rgba(59, 130, 246, 0.12));
}

@media (prefers-color-scheme: dark) {
  .rs-tab {
    background: rgba(15, 23, 42, 0.35);
    border-color: rgba(148, 163, 184, 0.22);
  }
  .rs-tab--active {
    border-color: rgba(129, 140, 248, 0.45);
    background: rgba(99, 102, 241, 0.2);
  }
}

.createForm {
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  padding: 12px;
  display: grid;
  gap: 10px;
}
@media (prefers-color-scheme: dark) {
  .createForm {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: end;
}
.field {
  display: grid;
  gap: 6px;
  min-width: 180px;
}
.field.grow {
  flex: 1;
  min-width: 240px;
}
label {
  font-size: 12px;
  opacity: 0.75;
  font-weight: 800;
}
label.muted {
  opacity: 0.5;
}
input,
select {
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.6);
}
@media (prefers-color-scheme: dark) {
  input,
  select {
    border-color: rgba(148, 163, 184, 0.22);
    background: rgba(15, 23, 42, 0.35);
    color: inherit;
  }
}
.btn {
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.4);
  color: inherit;
  border-radius: 12px;
  padding: 8px 10px;
  cursor: pointer;
  font-weight: 800;
}
.btn.primary {
  border-color: rgba(99, 102, 241, 0.28);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.95), rgba(59, 130, 246, 0.95));
  color: white;
}
.btn.danger {
  border-color: rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.1);
}
.table {
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  overflow: hidden;
}
@media (prefers-color-scheme: dark) {
  .table {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.tr {
  display: grid;
  grid-template-columns: 1fr 120px 120px minmax(280px, 1.2fr);
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}
.tr.th {
  border-top: 0;
  font-weight: 900;
  background: rgba(148, 163, 184, 0.14);
}
.tr--empty > div:first-child {
  grid-column: 1 / -1;
  font-size: 14px;
  opacity: 0.72;
}
.name {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
  font-weight: 900;
}
.name__text {
  min-width: 0;
  line-height: 1.35;
}
.badge {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 999px;
}
.badge--rent {
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.35);
}
.badge--sale {
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.35);
}
.money {
  font-weight: 900;
}
.money__unit {
  font-size: 12px;
  font-weight: 700;
  opacity: 0.65;
}
.tag {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(34, 197, 94, 0.25);
  background: rgba(34, 197, 94, 0.1);
  font-weight: 800;
}
.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

/* 详情弹窗（与首页商品详情风格一致） */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal.panel {
  width: 100%;
  max-width: 440px;
  max-height: 90vh;
  overflow: auto;
  border-radius: 16px;
  padding: 18px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(15, 23, 42, 0.1);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
}

@media (prefers-color-scheme: dark) {
  .modal.panel {
    background: rgba(15, 23, 42, 0.96);
    border-color: rgba(148, 163, 184, 0.2);
  }
}

.modal__title {
  font-size: 17px;
  font-weight: 900;
  margin-bottom: 12px;
}

.modal__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.detail-cover {
  margin-bottom: 12px;
  text-align: center;
}

.detail-cover img {
  max-width: 100%;
  max-height: 220px;
  border-radius: 12px;
  object-fit: contain;
  cursor: zoom-in;
  border: 1px solid rgba(15, 23, 42, 0.1);
}

@media (prefers-color-scheme: dark) {
  .detail-cover img {
    border-color: rgba(148, 163, 184, 0.2);
  }
}

.detail-row {
  font-size: 14px;
  margin-bottom: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.detail-row--block {
  flex-direction: column;
  align-items: stretch;
}

.detail-row--price {
  flex-wrap: nowrap;
  align-items: baseline;
}

.detail-price-value {
  white-space: nowrap;
}

.detail-row .k {
  font-weight: 800;
  opacity: 0.65;
  min-width: 4.5rem;
}

.desc {
  margin: 4px 0 0;
  opacity: 0.85;
  line-height: 1.5;
}
@media (max-width: 980px) {
  .tr {
    grid-template-columns: 1fr;
  }
  .tr.th {
    display: none;
  }
  .ops {
    justify-content: flex-start;
  }
}
</style>

