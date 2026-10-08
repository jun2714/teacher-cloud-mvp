export const MAX_MATERIAL_CHARS = 60000
export const DOCUMENT_EXTENSIONS = ['docx', 'pdf', 'jpg', 'jpeg', 'png', 'webp']
export const MEDIA_EXTENSIONS = ['mp3', 'wav', 'm4a', 'aac', 'amr', 'flac', 'ogg', 'wma', 'mp4', 'mov', 'webm', 'avi', 'mkv', 'mpeg', 'mpg']

export function classifyMaterial(file) {
  const extension = file.name.split('.').pop().toLowerCase()
  if (DOCUMENT_EXTENSIONS.includes(extension)) {
    if (file.size > 8 * 1024 * 1024) throw new Error('单个文档或图片不能超过 8MB')
    return 'document'
  }
  if (MEDIA_EXTENSIONS.includes(extension)) {
    if (file.size > 80 * 1024 * 1024) throw new Error('单个音视频不能超过 80MB')
    return 'media'
  }
  throw new Error('支持 .docx、PDF、JPG、PNG、WEBP 和常见音视频；旧版 .doc 请另存为 .docx')
}

export function appendMaterial(current, filename, text) {
  if (!text?.trim()) throw new Error('未识别到有效内容，请换一个文件或手动输入。')
  const result = [current.trim(), `【材料：${filename}】\n${text.trim()}`].filter(Boolean).join('\n\n')
  if (result.length > MAX_MATERIAL_CHARS) throw new Error('合并后的材料超过 60000 字，请拆分分析。')
  return result
}
