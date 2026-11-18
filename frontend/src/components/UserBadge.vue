<script setup>
defineProps({
  name: { type: String, required: true },
  avatar: { type: String, required: true },
})
</script>

<template>
  <div class="flex flex-col items-center">
    <img
      :src="avatar"
      width="40"
      height="40"
      alt=""
      class="size-[40px] rounded-full object-cover ring-1 ring-line-strong"
    />
    <span
      class="relative -mt-[9px] max-w-[160px] truncate rounded-full border border-line-strong bg-sidebar/85
        px-[8px] py-[1px] text-[11.5px] font-medium backdrop-blur-sm"
    >{{ name }}</span>
  </div>
</template>
