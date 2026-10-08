// Usage: node scripts/render_lesson_templates.mjs <artifact-tool module> <prepared directory> <assets directory>
import fs from 'node:fs/promises'
import path from 'node:path'
import { pathToFileURL } from 'node:url'
const [runtime, prepared, output] = process.argv.slice(2)
if (!runtime || !prepared || !output) throw new Error('Provide the artifact-tool module, prepared PPTX directory and assets directory')
const { PresentationFile, FileBlob } = await import(pathToFileURL(path.resolve(runtime)).href)
await fs.mkdir(output, { recursive: true })
for (const id of ['education-grey', 'research-purple', 'training-orange', 'teacher-grey']) {
  const deck = await PresentationFile.importPptx(await FileBlob.load(path.join(prepared, id + '.pptx')))
  if (deck.slides.items.length !== 2) throw new Error('Expected two prepared slides: ' + id)
  for (const [index, kind] of ['cover', 'content'].entries()) {
    const png = await deck.slides.items[index].export({ format: 'png', scale: 1 })
    await fs.writeFile(path.join(output, id + '-' + kind + '.png'), new Uint8Array(await png.arrayBuffer()))
  }
  console.log('Rendered ' + id)
}
