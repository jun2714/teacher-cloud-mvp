<script setup>
import { useRouter } from 'vue-router'
import NoticeBell from '../components/NoticeBell.vue'
import imgCap from '../assets/images/home-cap.png'
import imgAI from '../assets/images/home-chat.png'
import imgPencil from '../assets/images/home-pencil.png'
import imgLesson from '../assets/images/home-lesson-illus.png'
import imgHeadphone from '../assets/images/home-headphone.png'
import imgNoteIcon from '../assets/images/home-note-icon.png'
import imgRecLesson from '../assets/images/rec-lesson.png'
import imgRecNotes from '../assets/images/rec-notes.png'
import imgResBook from '../assets/images/res-book-banner.png'
import imgResChart from '../assets/images/res-chart-banner.png'

const router = useRouter()
</script>

<template>
  <main class="home">
    <header class="home-title">
      首页
      <NoticeBell class="home-bell" />
    </header>

    <!-- 顶部欢迎 / AI 智能体 -->
    <section class="hero" role="button" tabindex="0" @click="router.push('/assistant')">
      <div class="hero-head">
        <span class="hero-badge">
          <!-- <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="5" y="3" width="14" height="18" rx="2.5" stroke="#2563eb" stroke-width="1.8" />
            <path d="M9 8h6M9 12h6M9 16h4" stroke="#2563eb" stroke-width="1.8" stroke-linecap="round" />
          </svg> -->
          <img class="home-chat" :src="imgAI" alt="AI" />
        </span>
        <div>
          <b>您好，欢迎使用<span>教研云智能助手</span></b>
          <p>不止是回答，更是启迪——开启您的教学共创之旅</p>
        </div>
      </div>
      <div class="hero-panel">
        <div class="hero-panel-text">
          <strong>教研云智能助手</strong>
          <h2>AI 智能体平台</h2>
          <div class="chips">
            <span>高效便捷</span>
            <span>智能易用</span>
            <span>创新教学</span>
          </div>
        </div>
        <img class="hero-illus" :src="imgCap" alt="" />
      </div>
    </section>

    <!-- 教学设计辅助 -->
    <section class="lesson-card" @click="router.push('/lesson-design')">
      <img class="lesson-illus" :src="imgLesson" alt="" />
      <div class="lesson-head">
        <img class="lesson-icon" :src="imgPencil" alt="" />
        <h2>个人教学设计</h2>
      </div>
      <p class="lesson-desc">按跟岗研修个人教学设计格式生成，可用于第六天教学成果汇报</p>
      <ul class="lesson-list">
        <li><i>✓</i>十一项完整设计结构</li>
        <li><i>✓</i>含教学过程五列表格</li>
        <li><i>✓</i>对齐新课标与核心素养</li>
      </ul>
      <button type="button" @click.stop="router.push('/lesson-design')">使用 ›</button>
    </section>

    <!-- 精选推荐：横向滑动 -->
    <div class="section-bar">
      <h2>精选推荐</h2>
    </div>
    <section class="rec-scroll">
      <article class="rec-card" @click="router.push('/lesson-review')">
        <div class="rec-top">
          <img class="rec-icon" :src="imgHeadphone" alt="" />
          <b>听评课助手</b>
        </div>
        <p class="rec-desc">上传课堂录音/视频可自动转写成文字，再生成多维评课分析。</p>
        <img class="rec-cover" :src="imgRecLesson" alt="听评课助手" />
      </article>

      <article class="rec-card purple" @click="router.push('/notes')">
        <div class="rec-top">
          <img class="rec-icon" :src="imgNoteIcon" alt="" />
          <b>教研笔记</b>
        </div>
        <p class="rec-desc">随时记录灵感与思考，支持结构化整理与报告生成。</p>
        <img class="rec-cover" :src="imgRecNotes" alt="教研笔记" />
      </article>
    </section>

    <section class="resource" aria-label="精选优质课程资源">
      <h2>精选优质课程资源</h2>
      <p>覆盖多学段多学科，<span>一站式获取教学素材</span></p>
      <div class="resource-grid">
        <img class="res-banner" :src="imgResBook" alt="告别备课内耗，让教学更轻松" />
        <img class="res-banner" :src="imgResChart" alt="从走过场到真提升，教研实效提升" />
      </div>
    </section>
  </main>
</template>

<style scoped>
.home {
  padding-bottom: 20px;
  animation: fade-in 0.35s ease;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}

.home-title {
  height: 52px;
  display: grid;
  place-items: center;
  font-size: 17px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #e8ecf2;
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(16px);
}

.home-bell {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
}

.blend {
  /* 兼容旧引用；当前图标已去黑底 */
}

/* —— Hero —— */
.hero {
  margin: 12px 14px 14px;
  padding: 16px;
  border-radius: 22px;
  color: #fff;
  background: linear-gradient(145deg, #1a6dff 0%, #2f7bff 45%, #5b8dff 100%);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.22);
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.hero-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  position: relative;
  z-index: 1;
}

.hero-badge {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #fff;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.hero-badge svg {
  width: 22px;
  height: 22px;
}

.hero-head b {
  display: block;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.4;
}

.hero-head b span {
  color: #ffe566;
}

.hero-head p {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.78);
}

.hero-panel {
  margin-top: 14px;
  padding: 14px 14px 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.97);
  color: #1a2332;
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  z-index: 1;
  box-shadow: 0 8px 20px rgba(0, 40, 120, 0.1);
  overflow: hidden;
  min-height: 118px;
}

.hero-panel-text {
  flex: 1;
  min-width: 0;
  position: relative;
  z-index: 1;
}

.hero-panel strong {
  display: block;
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
}

.hero-panel h2 {
  margin: 6px 0 12px;
  font-size: 20px;
  font-weight: 800;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chips span {
  padding: 4px 9px;
  border-radius: 999px;
  background: #e8f1ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 500;
}
  
.home-chat {
  width: 42px;
  height: 42px;
}

.hero-illus {
  width: 112px;
  height: 112px;
  object-fit: contain;
  flex-shrink: 0;
  margin-right: -12px;
  /* 透明底插画，不再套白/深色方框 */
  filter: drop-shadow(0 8px 16px rgba(37, 99, 235, 0.2));
}

/* —— 教学设计（紧凑、左对齐） —— */
.lesson-card {
  margin: 0 14px 14px;
  padding: 10px 12px 10px;
  border-radius: 16px;
  background: linear-gradient(135deg, #ff9f1a 0%, #ff5c6c 100%);
  color: #fff;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(255, 100, 80, 0.2);
  text-align: left;
}

.lesson-head {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  z-index: 1;
  padding-right: 72px;
}

.lesson-icon {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  object-fit: contain;
  flex-shrink: 0;
  background: #fff;
  filter: drop-shadow(0 3px 8px rgba(120, 30, 20, 0.2));
}

.lesson-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  line-height: 1.2;
}

.lesson-desc {
  position: relative;
  z-index: 1;
  margin: 6px 0 5px;
  padding-right: 72px;
  font-size: 11px;
  line-height: 1.4;
  opacity: 0.92;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.lesson-list {
  position: relative;
  z-index: 1;
  list-style: none;
  margin: 0;
  padding: 0 88px 0 0;
  font-size: 11px;
  line-height: 1.45;
}

.lesson-list li {
  display: flex;
  align-items: center;
  gap: 5px;
}

.lesson-list i {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.28);
  display: grid;
  place-items: center;
  font-style: normal;
  font-size: 8px;
  font-weight: 700;
  flex-shrink: 0;
}

.lesson-illus {
  position: absolute;
  right: -6px;
  top: 50%;
  transform: translateY(-50%);
  width: 72px;
  height: 72px;
  object-fit: contain;
  pointer-events: none;
  opacity: 0.95;
}

.lesson-card > button {
  position: absolute;
  right: 10px;
  bottom: 10px;
  z-index: 2;
  border: 0;
  border-radius: 999px;
  background: #fff;
  color: #ef5a2a;
  padding: 5px 12px;
  font-weight: 700;
  font-size: 12px;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
}

/* —— 精选推荐 —— */
.section-bar {
  margin: 0 16px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-bar h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: #1a2332;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-bar h2::before {
  content: "";
  width: 3px;
  height: 16px;
  border-radius: 999px;
  background: #2563eb;
}

.section-bar button {
  border: 0;
  background: transparent;
  color: #94a3b8;
  font-size: 12px;
}

.rec-scroll {
  display: flex;
  gap: 12px;
  padding: 0 14px 16px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}

.rec-scroll::-webkit-scrollbar {
  display: none;
}

.rec-card {
  flex: 0 0 78%;
  scroll-snap-align: start;
  background: #fff;
  border: 1px solid #e8ecf2;
  border-radius: 16px;
  padding: 14px;
  box-shadow: 0 6px 18px rgba(26, 45, 90, 0.06);
  cursor: pointer;
  transition: transform 0.15s;
  overflow: hidden;
}

.rec-card.purple {
  background: #fff;
  box-shadow: 0 6px 18px rgba(26, 45, 90, 0.06);
}

.rec-card:active {
  transform: scale(0.985);
}

.rec-top {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}

.rec-icon {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  object-fit: cover;
  flex-shrink: 0;
  background: #f5f8fc;
}

.rec-top b {
  display: block;
  font-size: 15px;
  font-weight: 800;
  color: #1a2332;
  line-height: 1.3;
}

.rec-desc {
  margin: 0 0 10px;
  font-size: 12px;
  line-height: 1.55;
  color: #8a93a3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.rec-cover {
  width: 100%;
  aspect-ratio: 16 / 8;
  object-fit: cover;
  border-radius: 12px;
  display: block;
  background: #f5f8fc;
}

.resource {
  padding: 4px 14px 8px;
}

.resource > h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: #1a2332;
  display: flex;
  align-items: center;
  gap: 8px;
}

.resource > h2::before {
  content: "";
  width: 3px;
  height: 16px;
  border-radius: 999px;
  background: #2563eb;
}

.resource > p {
  margin: 6px 0 12px;
  font-size: 13px;
  color: #8a93a3;
}

.resource > p span {
  color: #2563eb;
  font-weight: 600;
}

.resource-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.res-banner {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 14px;
  object-fit: contain;
  box-shadow: 0 8px 18px rgba(26, 45, 90, 0.08);
  pointer-events: none;
  user-select: none;
}

@media (max-width: 360px) {
  .lesson-copy {
    padding-right: 0;
  }

  .lesson-illus {
    opacity: 0.3;
  }
}
</style>
