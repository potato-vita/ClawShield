<script setup lang="ts">import {onMounted} from "vue";import {useRuntimeStore} from "@/stores/runtimeStore";const store=useRuntimeStore();onMounted(()=>store.initialize());</script>
<template><router-view v-slot="{Component,route}"><Transition name="page" mode="out-in"><component :is="Component" :key="String(route.name)"/></Transition></router-view></template>
<style>.page-enter-active,.page-leave-active{transition:opacity 150ms ease,transform 180ms cubic-bezier(.2,.8,.2,1)}.page-enter-from{opacity:0;transform:translateY(4px)}.page-leave-to{opacity:0;transform:translateY(-2px)}</style>
