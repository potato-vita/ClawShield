<template>
  <div class="legend"><span><i class="tool" />工具调用</span><span><i class="object" />敏感对象</span><span><i class="sink" />不可信目标</span><span><i class="block" />已阻止</span></div>
</template>
<style scoped>.legend{display:flex;flex-wrap:wrap;gap:12px;color:#778293;font-size:8px}.legend span{display:flex;align-items:center;gap:5px}.legend i{width:7px;height:7px;border-radius:50%;background:#7f8b9a}.legend .object{background:#d38a18}.legend .sink,.legend .block{background:var(--trace-red)}.legend .block{border-radius:2px}</style>
