"""Evidence-based training reports. No invented assessments or model calls.

Counts use saved, in-period records. Text excerpts are attributed, thematic
matches are only discussion topics, and proposed actions are not achievements.
"""
import re
from collections import Counter
from functools import cached_property

from markdown_it import MarkdownIt
from django.utils import timezone

from .dashboard import CONTENT
from .guidance import BODY_FIELDS, display_name

LABELS = {key: label for key, label, *_ in CONTENT}
THEMES = (
    ('教学目标与课程理解', ('课标', '教学目标', '核心素养', '课程标准'), '选择一课，核对目标、活动和评价是否对应，形成一张对照表。'),
    ('课堂活动与学生参与', ('课堂互动', '小组', '合作学习', '主动提问', '参与度', '课堂活动'), '安排一次小组活动观察，记录学生参与表现并调整任务分工。'),
    ('学习评价与作业设计', ('评价', '互评', '作业', '量规', '反馈'), '共同修订一份评价量规，用一组匿名学生作品检验标准是否清晰。'),
    ('学情差异与分层支持', ('分层', '差异', '学困', '学习困难', '因材施教'), '围绕同一目标设计两种支持路径，记录不同学生的完成表现。'),
    ('数字工具与资源应用', ('数字', '信息技术', '人工智能', '录音', '课件', '多媒体'), '选择一种工具解决一个课堂问题，记录使用步骤及适用条件。'),
    ('教学反思与行动研究', ('反思', '改进', '行动研究', '课例研究', '教学研究'), '围绕一个具体问题完成“观察—调整—再观察”的简短实践记录。'),
)


def plain(value):
    """Readable excerpt without Markdown syntax, links, remote images or HTML."""
    tokens = MarkdownIt('js-default').parse(str(value or ''))
    parts = []
    for token in tokens:
        if token.type == 'inline':
            parts.append(''.join(t.content if t.type in ('text', 'code_inline', 'image') else ' '
                                 if t.type in ('softbreak', 'hardbreak') else '' for t in token.children or []))
        elif token.type in ('fence', 'code_block'):
            parts.append(token.content)
    return re.sub(r'\s+', ' ', ' '.join(parts)).strip()


def text(value):
    # Source text must never introduce report headings, tables, links or images.
    value = '' if value is None else str(value)
    return re.sub(r'([\\`*_{}\[\]()#+.!<>|~-])', r'\\\1', value.replace('\r', ' ').replace('\n', ' '))


def excerpt(value, limit=230):
    # Long generated documents often begin with a cover and teacher metadata.
    # Quote their substantive paragraphs instead of repeating the cover as a finding.
    whole = plain(value)
    paragraphs = []
    tokens = MarkdownIt('js-default').parse(str(value or ''))
    metadata = re.compile(r'^(?:教师姓名|姓名|所在单位|学校|学科|授课年级|年级|教材版本|课时安排|课题名称|指导教师|完成日期|跟岗时间|跟岗基地|说明)\s*[：:]')
    for i, token in enumerate(tokens):
        if token.type != 'inline' or (i and tokens[i - 1].type == 'heading_open'):
            continue
        candidate = plain(token.content)
        if not candidate or metadata.match(candidate) or candidate.startswith('吴忠中学教师跟岗实践'):
            continue
        paragraphs.append(candidate)
    value = ' '.join(paragraphs) or whole
    return text(value[:limit]) + ('……（节选）' if len(value) > limit or value != whole else '')


def table(headers, rows):
    return '\n'.join(['|' + '|'.join(map(text, headers)) + '|', '|' + '|'.join('---' for _ in headers) + '|'] +
                     ['|' + '|'.join(map(text, row)) + '|' for row in rows]) + '\n\n'


def percentage(n, total):
    return f'{n / total * 100:.1f}%' if total else '0.0%'


class TrainingEvidence:
    def __init__(self, data, groups, process, active, questions=(), messages=(), feedback=None):
        self.data, self.groups, self.process, self.active = data, groups, process, active
        self.profiles = data['profiles']
        self.questions, self.messages, self.feedback = list(questions), list(messages), feedback
        self.targets = {k: data.get('target_' + k) for k in LABELS if data.get('target_' + k)}
        self.captured_at = timezone.localtime().strftime('%Y-%m-%d %H:%M')

    def for_teacher(self, profile):
        uid = profile.user_id
        one = TrainingEvidence({**self.data, 'profiles': [profile],
                                'roster_rows': [r for r in self.data.get('roster_rows', []) if r['profile'].user_id == uid]},
                                {k: [r for r in rows if r.author_id == uid] for k, rows in self.groups.items()},
                                [r for r in self.process if r[0] == uid], {r for r in self.active if r[0] == uid},
                                [q for q in self.questions if q.author_id == uid],
                                [m for m in self.messages if m.chat.author_id == uid],
                                None if self.feedback is None else [f for f in self.feedback if f.teacher_id == uid])
        one.__dict__['sources'] = [s for s in self.sources if s['uid'] == uid]
        one.__dict__['filled'] = {k: [r for r in rows if r.author_id == uid] for k, rows in self.filled.items()}
        if self.data.get('official_rows'):
            one.data['official_rows'] = [r for r in self.data['official_rows'] if r['user_id'] == uid]
        return one

    @cached_property
    def counts(self):
        return {key: len(rows) for key, rows in self.groups.items()}

    @cached_property
    def filled(self):
        return {key: [r for r in rows if plain(getattr(r, BODY_FIELDS[key]))] for key, rows in self.groups.items()}

    @cached_property
    def sources(self):
        rows = []
        for kind, records in self.groups.items():
            for obj in records:
                rows.append({'ref': f'{LABELS[kind]} #{obj.pk}', 'title': obj.title, 'uid': obj.author_id,
                             'date': timezone.localtime(obj.created_at).strftime('%Y-%m-%d'),
                             'when': obj.created_at, 'body': getattr(obj, BODY_FIELDS[kind]), 'kind': kind})
        for q in self.questions:
            rows.append({'ref': f'社区提问 #{q.pk}', 'title': q.title, 'uid': q.author_id,
                         'date': timezone.localtime(q.created_at).strftime('%Y-%m-%d'), 'when': q.created_at, 'body': q.content, 'kind': 'question'})
        for m in self.messages:
            rows.append({'ref': f'教师提问 #{m.pk}', 'title': m.chat.title, 'uid': m.chat.author_id,
                         'date': timezone.localtime(m.created_at).strftime('%Y-%m-%d'), 'when': m.created_at, 'body': m.content, 'kind': 'message'})
        for row in rows:
            row['search_text'] = plain(row['title'] + '\n' + row['body'])
        return sorted(rows, key=lambda row: (row['when'], row['ref']))

    @cached_property
    def themes(self):
        result = []
        for label, words, action in THEMES:
            matches = [s for s in self.sources if any(word in s['search_text'] for word in words)]
            if matches:
                result.append((label, matches, action))
        return sorted(result, key=lambda row: (-len({s['uid'] for s in row[1]}), -len(row[1]), row[0]))

    def intro(self, purpose):
        body = f'培训批次：{text(self.data["batch_name"])}\n\n统计期间：{self.data["start"]} 至 {self.data["end"]}（含首尾日期）\n\n'
        body += f'报告生成时间：{self.captured_at}\n\n{purpose}\n\n'
        if self.data.get('roster_source'):
            body += '教师范围：' + text(self.data['roster_source']) + '。只纳入这些教师在上述期间创建的内容。\n\n'
        if self.data.get('official_rows'):
            from .official_roster import official_summary
            body += official_summary(self.data['official_rows']) + '未匹配或待核对人员仍保留在正式名单人数中，不纳入不确定账号的材料。未匹配不等于未参训。\n\n'
            body += table(['名单序号', '姓名', '学校', '学科', '账号核对状态'],
                          [(r['no'], r['name'], r['school'], r['subject'], r['status']) for r in self.data['official_rows']])
        if self.data.get('roster_rows'):
            roster = self.data['roster_rows']
            body += f'所选教师中，本期注册 {sum(r["registered"] for r in roster)} 人，有本期使用证据 {sum(r["used"] for r in roster)} 人（两项可重叠）。\n\n'
            body += '注册和使用时间仅为名单核对依据。使用证据包含保存内容及落在本期的最近一次登录；历史登录记录不完整，不能据此推断完整出勤。\n\n'
        if self.data.get('training_context'):
            body += '培训安排与目标（管理员补充）：' + text(self.data['training_context']) + '\n\n'
        if self.data.get('implementation_notes'):
            body += '线下实施及调查情况（管理员补充，未经平台核验）：' + text(self.data['implementation_notes']) + '\n\n'
        return body

    def participation(self):
        n = len(self.profiles)
        participating = len({uid for uid, _ in self.active})
        producers = len({r.author_id for rows in self.filled.values() for r in rows})
        return (f'本次选入 {n} 位教师，其中 {participating} 人有平台活动记录，记录覆盖率为 {percentage(participating, n)}；'
                f'{producers} 人保存了有正文的研修成果，覆盖率为 {percentage(producers, n)}。'
                f'累计保存成果 {sum(self.counts.values())} 份，其中有正文 {sum(map(len, self.filled.values()))} 份。'
                f'记录到 {len(self.process)} 次平台活动、{len(self.active)} 个教师活跃人日。'
                '这些数字说明资料留存和参与分布，不代表现场出勤、学习时长或教学能力。\n\n')

    def profile_distribution(self):
        rows = []
        for field, label in [('school_name', '学校'), ('subject', '学科'), ('grade', '年级')]:
            counts = Counter(getattr(p, field).strip() or '未填写' for p in self.profiles)
            rows.extend((label, value, count, percentage(count, len(self.profiles))) for value, count in sorted(counts.items()))
        return table(['类别', '档案登记内容', '教师数', '占所选教师比例'], rows)

    def material_summary(self):
        return table(['材料类型', '保存份数', '有正文份数', '有正文教师数'],
                     [(LABELS[k], self.counts[k], len(self.filled[k]), len({r.author_id for r in self.filled[k]})) for k in LABELS])

    def task_progress(self):
        if not self.targets:
            return '本次未填写每位教师的成果任务要求，因此不计算任务完成率。下面的材料覆盖情况仅用于核对资料。\n\n'
        met = 0
        rows = []
        for p in self.profiles:
            detail, passed = [], True
            for k, target in self.targets.items():
                count = sum(r.author_id == p.user_id for r in self.filled[k])
                detail.append(f'{LABELS[k]} {count}/{target}')
                passed &= count >= target
            met += passed
            rows.append((f'{display_name(p.user)}（{p.user_id}）', '；'.join(detail), '达到数量要求' if passed else '待补齐'))
        body = '按管理员本次填写的每人最低份数核对：' + '；'.join(f'{LABELS[k]} {n} 份' for k, n in self.targets.items()) + '。只计有正文记录，重复提交是否合格仍需审核。\n\n'
        body += f'{met}/{len(self.profiles)} 人达到所填全部数量要求，比例为 {percentage(met, len(self.profiles))}。这不是成果质量审核或结业通过率。\n\n'
        return body + table(['教师（编号）', '有正文份数/要求', '数量核对'], rows)

    def learning_needs(self):
        body = ''
        if self.themes:
            body += '按已保存正文和教师提问中的主题词归纳讨论方向；同一材料可涉及多个主题。提及某主题不表示教师在该方面存在能力不足。\n\n'
            body += table(['材料涉及主题', '教师数', '材料数', '可开展的研修活动'],
                          [(label, len({s['uid'] for s in matches}), len(matches), action) for label, matches, action in self.themes])
        else:
            body += '目前未从所选材料提取到可归纳的研修主题，建议通过教师需求问卷或访谈进一步确认。\n\n'
        questions = [s for s in self.sources if s['kind'] in ('question', 'message')]
        body += f'教师主动提问共 {len(questions)} 条，涉及 {len({s["uid"] for s in questions})} 人。以下为近期问题节选，按时间倒序列出最多 6 条，作为跟进线索：\n\n'
        for s in list(reversed(questions))[:6]:
            body += self.quote(s)
        if not questions:
            body += '本期未记录教师主动提问，不能据此认定没有学习困难或培训需求。\n\n'
        return body

    def quote(self, source):
        names = {p.user_id: display_name(p.user) for p in self.profiles}
        return (f'- {text(names[source["uid"]])}（教师编号 {source["uid"]}） · {text(source["ref"])} · {source["date"]} · '
                f'{text(source["title"])}\n\n> {excerpt(source["body"] or source["title"])}\n\n')

    def gaps_and_actions(self):
        rows = []
        inactive = [p for p in self.profiles if not any(uid == p.user_id for uid, _ in self.active)]
        if inactive:
            rows.append((f'{len(inactive)} 人无本期平台活动记录', '核实账号使用和线下参训情况，提供上传辅导；不能直接判定缺勤。', '培训管理员', '下次研修前', '核实记录及补交资料'))
        for k in LABELS:
            missing = len(self.profiles) - len({r.author_id for r in self.filled[k]})
            if missing:
                rows.append((f'{missing} 人暂无有正文的{LABELS[k]}', f'核实本批次是否要求{LABELS[k]}；需要时安排指导和补交。', '指导教师与参训教师', '本批次资料核对时', f'{LABELS[k]}正文及审核意见'))
        for label, _, action in self.themes[:2]:
            rows.append((f'材料涉及{label}', action, '学科教研组', '下一轮教研', '修订材料与课堂观察记录'))
        rows.append(('尚无统一前后测证据', '按培训目标设计同口径问卷或任务评价，保留原始结果后再判断变化。', '培训负责人', '下轮培训前后', '同口径测评或问卷结果'))
        return table(['记录反映的情况', '建议行动', '建议负责人', '建议时点', '需留存证据'], rows)

    def feedback_section(self):
        if self.feedback is None:
            return '当前账号无教研指导查看权限，本次报告未纳入指导反馈。\n\n'
        if not self.feedback:
            return '本期未检索到已发送的指导反馈；草稿不作为已开展指导的证据。\n\n'
        completed = sum(bool(f.completed_at and timezone.localdate(f.completed_at) <= self.data['end']) for f in self.feedback)
        body = f'本期已发送指导 {len(self.feedback)} 条，其中截至期末有落实时间记录 {completed} 条。落实说明为教师提交，需结合实际材料核验。\n\n'
        for f in self.feedback[:5]:
            # Do not include subsequently edited reply text in a historical completion claim.
            body += f'- 指导 #{f.pk} · {text(f.target_title)}：{excerpt(f.suggestions)}\n\n'
            if f.action_plan:
                body += '建议行动：' + excerpt(f.action_plan) + '\n\n'
        if len(self.feedback) > 5:
            body += '以上列出前 5 条指导，完整记录可在后台“教研指导”查看。\n\n'
        return body

    def source_index(self):
        body = '正文采用材料节选；下表列出本报告分析所用全部成果及提问的定位信息。完整成果可同时选择“学员研修成果”导出。\n\n'
        if not self.sources:
            return body + '当前范围无可引用的成果正文或提问。\n\n'
        names = {p.user_id: display_name(p.user) for p in self.profiles}
        return body + table(['来源编号', '教师（编号）', '标题', '创建日期'],
                            [(s['ref'], f'{names[s["uid"]]}（{s["uid"]}）', s['title'], s['date']) for s in self.sources])

    def boundary(self):
        return ('本报告依据所选教师、日期及导出时仍保留的平台记录自动整理，供负责人或教师核对后使用。'
                '日期按创建时间筛选，正文与档案为导出时最新值，不是历史版本快照；线下活动仅引用管理员补充内容。'
                '活跃统计包含保存成果、社区提问/教师回答和向智能体提问，不含仅登录、浏览及 AI 回复。'
                '本报告未读取学生测评分数，不将教学设计中的“学生学情”混作参训教师学情。'
                '没有问卷、前后测、现场考勤或专家审核证据时，不推断满意度、能力提升、培训学时或验收结论。\n\n')


def batch_analysis(e):
    body = e.intro('本报告分析本批次参训教师的参与情况、研修材料、学习关注点和支持需求，供培训负责人调整指导安排。')
    body += '## 一 参训教师基础与研修概况\n\n' + e.participation()
    body += ('姓名、学校和学科以正式名单为准，名单未提供的年级不推断。' if e.data.get('official_rows') else '教师基础信息以当前档案登记为准。')
    body += '尚未收集教龄、职称和训前能力测评，不能仅凭学科年级判断起点能力。\n\n' + e.profile_distribution()
    body += '## 二 学习参与与材料完成情况\n\n' + e.material_summary() + e.task_progress()
    body += '## 三 学习关注点与具体需求\n\n' + e.learning_needs()
    body += '## 四 分层支持安排\n\n'
    n_active = len({uid for uid, _ in e.active})
    n_authors = len({r.author_id for rows in e.filled.values() for r in rows})
    body += table(['支持对象', '人数', '指导重点'], [
        ('无本期平台活动记录', len(e.profiles) - n_active, '先核实参训和账号使用情况，再安排操作辅导或补录。'),
        ('有活动但暂无有正文成果', n_active - n_authors, '从一个真实课堂问题入手，指导形成笔记或教学设计。'),
        ('已有有正文成果', n_authors, '结合原文进行同伴互评，围绕具体问题开展修订和课堂验证。')])
    body += '以上为资料状态分组，不是教师能力分级。\n\n' + e.gaps_and_actions()
    body += '## 五 已有指导与后续评价\n\n' + e.feedback_section()
    body += '建议先核对名单和材料，再对照教师提出的实际问题安排专题研修，并在后续课堂中收集相同口径的观察证据。\n\n'
    return body + '## 六 数据依据与使用说明\n\n' + e.boundary() + e.source_index()


def batch_summary(e):
    body = e.intro('本报告汇总本批次实际留存的研修过程、成果和问题，并形成后续改进安排，供培训总结和资料归档使用。')
    body += '## 一 本批次研修概况\n\n' + e.participation()
    if not e.data.get('training_context'):
        body += '本次未补充培训方案和具体目标，以下按平台实际记录梳理实施情况。\n\n'
    body += '## 二 研修实施过程\n\n'
    period_counts = {}
    for uid, kind, _, _, when in e.process:
        day = timezone.localdate(when)
        index = (day - e.data['start']).days // 7
        item = period_counts.setdefault(index, {'teachers': set(), 'types': Counter()})
        item['teachers'].add(uid)
        item['types'][kind] += 1
    from datetime import timedelta
    rows = []
    for index, value in sorted(period_counts.items()):
        start = e.data['start'] + timedelta(days=index * 7)
        end = min(start + timedelta(days=6), e.data['end'])
        rows.append((f'{start} 至 {end}', len(value['teachers']), '；'.join(f'{k} {v} 次' for k, v in value['types'].items())))
    body += table(['记录时段', '活动教师数', '留存活动'], rows) if rows else '本期尚无平台过程记录。\n\n'
    body += '按 7 天归并有记录的时段；未列出的时段无平台活动记录。保存材料时间不一定是线下教学或研修发生时间。\n\n'
    body += '## 三 研修成果与任务核对\n\n' + e.material_summary() + e.task_progress()
    body += '## 四 实践内容与阶段认识\n\n'
    body += e.learning_needs()
    body += '以下按材料类型选取最近一份有正文材料作内容示例，不代表评优或效果鉴定：\n\n'
    for kind in LABELS:
        samples = [s for s in e.sources if s['kind'] == kind and plain(s['body'])]
        if samples:
            body += e.quote(samples[-1])
    body += '现有材料可作为后续共同备课、课例研讨和成果修订的依据；是否改善课堂教学，需要结合课堂观察和学生学习证据再评价。\n\n'
    body += '## 五 指导反馈与存在的问题\n\n' + e.feedback_section()
    body += '## 六 后续改进安排\n\n' + e.gaps_and_actions()
    body += '## 七 归档核对与成果目录\n\n'
    body += '归档时请核对参训名单、任务要求、教师确认情况及线下实施材料；当前自动报告不代替专家评价或验收签署。\n\n'
    return body + e.boundary() + e.source_index()


def personal_report(e):
    p = e.profiles[0]
    body = e.intro('本报告根据该教师在所选期间的笔记、教学设计、听评课、已有报告及提问整理个人研修情况。建议由教师核对、补充亲身实践和反思后使用。')
    body += f'教师：{text(display_name(p.user))}（编号 {p.user_id}）\n\n学校：{text(p.school_name)}；学科：{text(p.subject)}；年级：{text(p.grade)}\n\n'
    body += '## 一 个人研修过程\n\n' + e.participation() + e.material_summary()
    if not any(e.filled.values()) and not e.questions and not e.messages:
        body += '## 资料待补充\n\n当前范围缺少可用于撰写学习内容与反思的正文或提问，本文件是材料核对稿，不代表个人研修报告已完成。请补充笔记或实践材料后重新生成。\n\n'
    if e.process:
        first, last = timezone.localtime(e.process[0][4]), timezone.localtime(e.process[-1][4])
        body += f'本期首条记录为 {first:%Y-%m-%d}，末条记录为 {last:%Y-%m-%d}。\n\n'
    body += '## 二 学习内容与教学实践整理\n\n'
    for kind in LABELS:
        samples = [s for s in e.sources if s['kind'] == kind and plain(s['body'])]
        body += f'### {LABELS[kind]}\n\n'
        if not samples:
            body += '本期暂无有正文记录，待教师补充相关实践。\n\n'
            continue
        body += f'本期留存有正文材料 {len(samples)} 份。以下按时间倒序摘录最多 2 份内容，完整目录见报告末尾：\n\n'
        for s in list(reversed(samples))[:2]:
            body += e.quote(s)
    body += '## 三 关注问题与反思线索\n\n' + e.learning_needs()
    body += '上述内容来自已保存材料，教师可据此补充“实际尝试了什么、观察到什么、下一步如何调整”，避免将教学设想写成已验证的成果。\n\n'
    body += '## 四 指导反馈与任务核对\n\n' + e.feedback_section() + e.task_progress()
    body += '## 五 下一步实践计划\n\n以下为根据资料状态和关注主题提出的建议，尚不表示教师已经承诺或完成：\n\n' + e.gaps_and_actions()
    return body + '## 六 资料来源与核对说明\n\n' + e.boundary() + e.source_index()


def report_documents(e):
    """Same source for HTML preview and Word export; keys enforce selected scope."""
    docs = []
    if 'B6' in e.data['categories']:
        docs.append({'key': 'B6', 'title': '本批次学情分析报告', 'body': batch_analysis(e), 'filename': '本批次学情分析报告.docx'})
    if 'B7' in e.data['categories']:
        docs.append({'key': 'B7', 'title': '本批次研修总结报告', 'body': batch_summary(e), 'filename': '本批次研修总结报告.docx'})
    if 'D1' in e.data['categories']:
        for p in e.profiles:
            one = e.for_teacher(p)
            docs.append({'key': f'D1:{p.user_id}', 'title': f'{display_name(p.user)}个人教研报告',
                         'body': personal_report(one), 'filename': f'教师个人教研报告/{p.user_id}_{display_name(p.user)}.docx'})
    return docs
