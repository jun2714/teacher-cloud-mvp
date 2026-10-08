# 教学设计 PPT 模板素材

这八张背景由用户提供的四个 PPTX 文件生成，各取第 1 页封面和第 4 页正文的基础背景、章节标记。封面插画、正文背景和配色来自原模板；示例文字、占位 Logo、示例图表及署名字段已去除。没有修改用户的原始文件。

| 素材前缀 | 原始文件 |
| --- | --- |
| education-grey | 灰色简约教育通用.pptx |
| research-purple | 紫色教研培训报演示模板.pptx |
| training-orange | 橙黄扁平简约教育培训模版.pptx |
| teacher-grey | 灰色简约教师述职演示模板.pptx |

背景以 1280 × 720 PNG 保留。教学文字由 `lessonSlides.js` 按各封面的留白位置生成，浏览器与 PPTX 共用位置、字号、颜色、对齐方式。PPTX 的背景装饰为图片，课题、个人信息、正文和页码为可编辑文本。

重新生成：先运行 `scripts/prepare_lesson_templates.py <原始文件目录> <临时输出目录>`，再运行 `scripts/render_lesson_templates.mjs <artifact-tool 模块路径> <临时输出目录> <本目录>`。脚本只读取原始 PPTX，不依赖下载目录在生产环境中存在。原文件和中间副本不参与网站运行。
