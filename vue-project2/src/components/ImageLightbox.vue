<script setup>
import { onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  src: { type: String, default: '' },
  alt: { type: String, default: '' },
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['update:open'])

function close() {
  emit('update:open', false)
}

function onKeydown(e) {
  if (e.key === 'Escape' && props.open) close()
}

watch(
  () => props.open,
  (v) => {
    if (typeof document === 'undefined') return
    document.body.style.overflow = v ? 'hidden' : ''
  },
)

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  if (typeof document !== 'undefined') document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open && src"
      class="image-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label="大图预览"
      @click.self="close"
    >
      <button type="button" class="image-lightbox__close" aria-label="关闭" @click="close">×</button>
      <img :src="src" :alt="alt" class="image-lightbox__img" />
    </div>
  </Teleport>
</template>

<style scoped>
.image-lightbox {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(2, 6, 23, 0.88);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: max(16px, env(safe-area-inset-top)) max(16px, env(safe-area-inset-right))
    max(16px, env(safe-area-inset-bottom)) max(16px, env(safe-area-inset-left));
  cursor: zoom-out;
  animation: image-lightbox-fade 0.18s ease-out;
}

@keyframes image-lightbox-fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.image-lightbox__img {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
  border-radius: 10px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.45);
  cursor: default;
  user-select: none;
  -webkit-user-drag: none;
}

.image-lightbox__close {
  position: fixed;
  top: max(12px, env(safe-area-inset-top));
  right: max(12px, env(safe-area-inset-right));
  z-index: 1;
  width: 44px;
  height: 44px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.55);
  color: #fff;
  font-size: 26px;
  line-height: 1;
  cursor: pointer;
  display: grid;
  place-items: center;
  backdrop-filter: blur(8px);
}

.image-lightbox__close:hover {
  background: rgba(15, 23, 42, 0.75);
}
</style>
