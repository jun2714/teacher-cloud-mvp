<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '../components/PageHeader.vue'
import SuggestInput from '../components/SuggestInput.vue'
import { useAuthStore } from '../stores/auth'
import { GRADES, SUBJECTS } from '../constants/options'
import { loadTeacherProfile } from '../composables/useTeacherProfile'

const router = useRouter()
const auth = useAuthStore()
const saving = ref(false)
const message = ref('')
const fileInput = ref(null)
const avatarPreview = ref('')
const avatarFile = ref(null)

const form = ref({
  display_name: '',
  school_name: '',
  department: '',
  subject: '',
  grade: '',
})

const avatarSrc = computed(() => avatarPreview.value || auth.user?.profile?.avatar_url || '')

onMounted(async () => {
  const profile = await loadTeacherProfile()
  form.value = {
    display_name: profile.display_name,
    school_name: profile.school_name,
    department: profile.department,
    subject: profile.subject,
    grade: profile.grade,
  }
  avatarPreview.value = auth.user?.profile?.avatar_url || ''
})

function pickAvatar() {
  fileInput.value?.click()
}

function onAvatarChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    message.value = '请选择图片文件'
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    message.value = '头像不能超过 5MB'
    return
  }
  avatarFile.value = file
  message.value = ''
  const reader = new FileReader()
  reader.onload = () => {
    avatarPreview.value = String(reader.result || '')
  }
  reader.readAsDataURL(file)
}

async function save() {
  if (!form.value.display_name.trim()) {
    message.value = '请填写姓名'
    return
  }
  saving.value = true
  message.value = ''
  try {
    const fd = new FormData()
    fd.append('display_name', form.value.display_name.trim())
    fd.append('school_name', form.value.school_name.trim())
    fd.append('department', form.value.department.trim())
    fd.append('subject', form.value.subject.trim())
    fd.append('grade', form.value.grade.trim())
    if (avatarFile.value) fd.append('avatar', avatarFile.value)
    await auth.updateProfile(fd)
    message.value = '保存成功'
    setTimeout(() => router.back(), 600)
  } catch (e) {
    message.value = e.response?.data?.detail || '保存失败，请稍后重试'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <main class="sub-page">
    <PageHeader title="个人信息" back />
    <div class="page-body">
      <section class="profile-preview">
        <button class="preview-avatar" type="button" @click="pickAvatar">
          <img v-if="avatarSrc" :src="avatarSrc" alt="头像" />
          <span v-else class="avatar-placeholder">上传</span>
          <em class="avatar-edit">换</em>
        </button>
        <div>
          <b>{{ form.display_name || '未填写姓名' }}</b>
          <p>{{ form.school_name || '未填写学校' }} · {{ form.department || '未填写教研组' }}</p>
          <small @click="pickAvatar">点击头像更换照片</small>
        </div>
        <input
          ref="fileInput"
          class="avatar-input"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          @change="onAvatarChange"
        />
      </section>

      <section class="form-card">
        <label>
          姓名
          <input v-model="form.display_name" maxlength="30" placeholder="例如：张老师" />
        </label>
        <label>
          学校
          <input v-model="form.school_name" maxlength="100" placeholder="例如：吴忠市吴忠中学" />
        </label>
        <label>
          教研组
          <input v-model="form.department" maxlength="100" placeholder="例如：高一语文组" />
        </label>
        <div class="two-col">
          <label>
            学科
            <SuggestInput v-model="form.subject" :options="SUBJECTS" placeholder="可选择或填写" />
          </label>
          <label>
            年级
            <SuggestInput v-model="form.grade" :options="GRADES" placeholder="可选择或填写" />
          </label>
        </div>
        <p v-if="message" class="form-tip" :class="{ ok: message === '保存成功' }">{{ message }}</p>
        <button class="primary-button" type="button" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存修改' }}
        </button>
        <button class="secondary-button pwd-link" type="button" @click="router.push('/settings')">修改密码</button>
      </section>
    </div>
  </main>
</template>

<style scoped>
.profile-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  padding: 16px;
  border-radius: 16px;
  background: linear-gradient(145deg, #1a6dff 0%, #2f7bff 50%, #5b8dff 100%);
  color: #fff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.2);
  position: relative;
}

.preview-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.18);
  display: grid;
  place-items: center;
  flex-shrink: 0;
  padding: 0;
  overflow: hidden;
  position: relative;
  cursor: pointer;
}

.preview-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.avatar-placeholder {
  font-size: 13px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.92);
}

.avatar-edit {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  color: #1a6dff;
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
  display: grid;
  place-items: center;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
}

.profile-preview b {
  display: block;
  font-size: 17px;
  font-weight: 800;
}

.profile-preview p {
  margin: 4px 0 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.82);
}

.profile-preview small {
  display: inline-block;
  margin-top: 6px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.9);
  text-decoration: underline;
  cursor: pointer;
}

.avatar-input {
  display: none;
}

.form-tip {
  margin: 0 0 10px;
  font-size: 13px;
  color: #f04438;
  text-align: left;
}

.form-tip.ok {
  color: #12b76a;
}

.pwd-link {
  width: 100%;
  margin-top: 10px;
  min-height: 44px;
}
</style>
