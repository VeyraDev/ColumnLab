<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const isRegister = ref(false)

const form = reactive({
  username: '',
  email: '',
  password: '',
})

async function submit() {
  loading.value = true
  try {
    if (isRegister.value) {
      await userStore.register({
        username: form.username,
        email: form.email,
        password: form.password,
      })
      ElMessage.success('注册成功')
    } else {
      await userStore.login({
        username: form.username,
        password: form.password,
      })
      ElMessage.success('登录成功')
    }
    await router.push('/workspace')
  } catch {
    // errors handled by axios interceptor
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1>ColumnLab</h1>
      <p class="subtitle">列式存储引擎观测台</p>
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item v-if="isRegister" label="邮箱">
          <el-input v-model="form.email" type="email" autocomplete="email" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" autocomplete="current-password" show-password />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" class="submit-btn">
          {{ isRegister ? '注册' : '登录' }}
        </el-button>
      </el-form>
      <button type="button" class="toggle-mode" @click="isRegister = !isRegister">
        {{ isRegister ? '已有账号？登录' : '没有账号？注册' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-app);
  padding: 16px;
}

.login-card {
  width: 100%;
  max-width: 360px;
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  padding: 24px;
}

h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.subtitle {
  margin: 4px 0 20px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.submit-btn {
  width: 100%;
  margin-top: 4px;
}

.toggle-mode {
  margin-top: 12px;
  width: 100%;
  border: none;
  background: none;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
