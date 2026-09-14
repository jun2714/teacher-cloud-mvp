import json
import os
import time
import urllib.error
import urllib.request

from services.text_clean import strip_required_marks

class AIServiceError(RuntimeError):
    pass


def _call_openai_compatible(system_prompt: str, user_prompt: str) -> str:
    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    api_key = os.getenv("AI_API_KEY", "")
    model = os.getenv("AI_MODEL", "gpt-4.1-mini")
    if not api_key:
        raise AIServiceError("未配置 AI_API_KEY")

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.5,
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise AIServiceError(f"AI 接口调用失败：{exc}") from exc


def generate_text(task: str, payload: dict) -> str:
    provider = os.getenv("AI_PROVIDER", "mock")
    user_prompt = _build_prompt(task, payload)
    system_prompt = (
        "你是一名严谨、务实的学校教研助手。输出必须可执行，不夸大，不评价教师能力，"
        "涉及课堂分析时应说明结论仅供参考。"
        "字段标题不要加必填星号 *。"
    )
    if provider == "bailian":
        return strip_required_marks(_call_bailian_app(user_prompt))
    if provider == "openai_compatible":
        return strip_required_marks(_call_openai_compatible(system_prompt, user_prompt))
    return strip_required_marks(_mock_text(task, payload))


def generate_text_stream(task: str, payload: dict):
    provider = os.getenv("AI_PROVIDER", "mock")
    user_prompt = _build_prompt(task, payload)
    if provider == "bailian":
        yield from _call_bailian_app_stream(user_prompt)
        return
    if provider == "openai_compatible":
        yield generate_text(task, payload)
        return
    text = _mock_text(task, payload)
    step = 16
    for index in range(0, len(text), step):
        yield text[index:index + step]
        time.sleep(0.02)


def _call_bailian_app_stream(user_prompt: str):
    api_key = os.getenv("AI_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")
    app_id = os.getenv("BAILIAN_APP_ID", "")
    base_url = os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/api/v1").rstrip("/")
    if not api_key:
        raise AIServiceError("未配置百炼 API Key（AI_API_KEY）")
    if not app_id:
        raise AIServiceError("未配置百炼应用 ID（BAILIAN_APP_ID）")

    body = json.dumps({
        "input": {"prompt": user_prompt},
        "parameters": {"has_thoughts": False, "incremental_output": True},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/apps/{app_id}/completion",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    last = ""
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            for raw in response:
                line = raw.decode("utf-8", errors="ignore").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    data = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                output = data.get("output") or {}
                text = str(output.get("text") or "")
                if text:
                    if last and text.startswith(last):
                        delta = text[len(last):]
                        last = text
                    else:
                        delta = text
                        last += text
                    if delta:
                        yield delta
                reason = str(output.get("finish_reason") or "").lower()
                if reason in ("stop", "completed"):
                    break
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            err = json.loads(body)
            message = err.get("message") or err.get("Message") or body
        except Exception:
            message = body or str(exc)
        raise AIServiceError(f"百炼应用调用失败：{message}") from exc
    except AIServiceError:
        raise
    except Exception as exc:
        raise AIServiceError(f"百炼应用调用失败：{exc}") from exc


def _call_bailian_app(user_prompt: str) -> str:
    api_key = os.getenv("AI_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")
    app_id = os.getenv("BAILIAN_APP_ID", "")
    base_url = os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/api/v1").rstrip("/")
    if not api_key:
        raise AIServiceError("未配置百炼 API Key（AI_API_KEY）")
    if not app_id:
        raise AIServiceError("未配置百炼应用 ID（BAILIAN_APP_ID）")

    payload = json.dumps({
        "input": {"prompt": user_prompt},
        "parameters": {"has_thoughts": False},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/apps/{app_id}/completion",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            err = json.loads(body)
            message = err.get("message") or err.get("Message") or body
        except Exception:
            message = body or str(exc)
        raise AIServiceError(f"百炼应用调用失败：{message}") from exc
    except Exception as exc:
        raise AIServiceError(f"百炼应用调用失败：{exc}") from exc

    output = data.get("output") or {}
    text = output.get("text") or ""
    if not str(text).strip():
        raise AIServiceError(data.get("message") or "百炼应用未返回正文")
    return str(text).strip()


def _build_prompt(task: str, payload: dict) -> str:
    if task == "assistant_chat":
        history = payload.get("history") or []
        lines = []
        for item in history[-12:]:
            role = "教师" if item.get("role") == "user" else "助手"
            lines.append(f"{role}：{item.get('content') or ''}")
        conversation = "\n".join(lines) or "（新对话）"
        file_block = ""
        if payload.get("file_name"):
            file_block = (
                f"教师上传文件：{payload.get('file_name')}\n"
                f"文件摘录：\n{payload.get('file_excerpt') or '（无可用正文）'}\n"
            )
        data = {
            "title": "教研助手对话",
            "content": (
                f"教师背景：学科{payload.get('subject') or '未提供'}，"
                f"年级{payload.get('grade') or '未提供'}，"
                f"学校{payload.get('school_name') or '未提供'}。\n"
                f"对话记录：\n{conversation}\n"
                f"{file_block}"
                f"教师本轮问题：{payload.get('message') or ''}\n"
                "请直接回答本轮问题。若有上传文件，请基于文件内容给出分析与可执行建议。"
                "不要输出完整教案或总结报告模板。"
            ),
            "subject": payload.get("subject") or "",
            "grade": payload.get("grade") or "",
            "tags": ["教研对话", "智能助手"],
        }
        extra = (
            "用简体中文直接给出可执行建议，对齐普通高中新课标。"
            "不评价教师能力，不输出思考过程，不要复述任务类型或 JSON。"
        )
        return (
            f"任务类型：question_answer\n"
            f"输入资料：\n{json.dumps(data, ensure_ascii=False, indent=2)}\n\n"
            f"{extra}"
        )
    extra = OUTPUT_SPECS.get(task, "请使用清晰的小标题输出。")
    return (
        f"任务类型：{task}\n"
        f"输入资料：\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        f"{extra}\n\n"
        f"注意：字段标题写成「姓名：」「所在单位：」即可，不要加必填星号 *。"
    )


OUTPUT_SPECS = {
    "lesson_plan": """请严格按下列 Markdown 结构输出「跟岗研修个人教学设计」，不要增减一级标题，不要输出思考过程。

# 跟岗研修个人教学设计

吴忠中学“组团帮扶”教师跟岗研修项目 · 泉州一中跟岗基地

> 说明：本表为跟岗期间需完成的个人教学设计成果，将在第六天进行教学成果汇报。

**教师姓名**：{用输入 teacher_name}
**所在单位**：{用输入 school_name，默认吴忠市吴忠中学}
**学科**：
**授课年级**：
**教材版本**：
**课时安排**：
**课题名称**：
**指导教师**：
**完成日期**：

## 一、教材分析
写清教材地位与作用、知识结构、内容特点。

## 二、学情分析
写清学生已有知识基础、认知特点、学习困难。必须吸收 student_context。

## 三、教学目标
按学科核心素养维度设计（知识与技能、过程与方法、情感态度价值观 / 学科核心素养）。

## 四、教学重点与难点
重点：
难点：
突破策略：

## 五、教学方法与策略
写明选用的教学方法、教学策略及理论依据。

## 六、教学资源准备
教具、多媒体资源、实验器材、学习单等。

## 七、教学过程设计
必须使用 Markdown 表格，列：环节 | 教师活动 | 学生活动 | 设计意图 | 时间分配
行至少包含：导入新课、新知探究、合作学习、巩固练习、课堂小结、作业布置。

## 八、板书设计
## 九、作业设计
分层作业、实践性作业、拓展性作业。
## 十、教学评价设计
课堂评价方式、评价工具、反馈机制。
## 十一、教学反思
教学设计亮点、可能存在的不足、改进方向。

**指导教师评语**

指导教师签字：__________    日期：____年__月__日
""",
    "note_report": """请严格按下列 Markdown 结构输出「跟岗研修总结报告」，不要增减一级标题。综合所选笔记，不要编造笔记中没有的事实。字数尽量贴近各节要求。

# 跟岗研修总结报告

吴忠中学“组团帮扶”教师跟岗研修项目 · 泉州一中跟岗基地

> 说明：跟岗研修结束后撰写，全面总结研修期间的学习收获、反思感悟与返校行动计划。

**姓名**：
**所在单位**：{默认吴忠市吴忠中学}
**学科/年级**：
**跟岗时间**：____年__月__日 至 ____年__月__日（有输入则用输入）
**跟岗基地**：福建省泉州第一中学（可用输入覆盖）
**指导教师**：
**报告日期**：

## 一、研修概况
约300字。时间、地点、主要活动内容及参与情况。

## 二、主要收获
约800字。从教育教学理念、课堂教学改革、课程体系建设、教研活动组织、学校管理经验等方面梳理。

## 三、重点学习成果
约500字。结合个人教学设计或笔记，写掌握的方法、策略或技能，以及如何体现在教学中。

## 四、对比与反思
约500字。对照泉州一中实践，反思自身差距与不足并分析原因。

## 五、返校行动计划
约500字。回吴忠中学后的改进计划，目标明确、措施具体、可操作。含个人教学、教研组建设、课程开发、示范辐射等。

## 六、意见与建议
约200字。对项目组织安排、内容设计、导师指导的意见建议。

**学员签字**

日期：____年__月__日

**指导教师评语**

指导教师签字：__________    日期：____年__月__日
""",
}


def _mock_text(task: str, payload: dict) -> str:
    if task == "lesson_plan":
        topic = payload.get("topic", "本课")
        return f"""# 跟岗研修个人教学设计

吴忠中学“组团帮扶”教师跟岗研修项目 · 泉州一中跟岗基地

> 说明：本表为跟岗期间需完成的个人教学设计成果，将在第六天进行教学成果汇报。

**教师姓名**：{payload.get("teacher_name") or "未填写"}
**所在单位**：{payload.get("school_name") or "吴忠市吴忠中学"}
**学科**：{payload.get("subject") or "未提供"}
**授课年级**：{payload.get("grade") or "未提供"}
**教材版本**：{payload.get("textbook") or "未提供"}
**课时安排**：{payload.get("class_hours") or 1}课时
**课题名称**：{topic}
**指导教师**：{payload.get("advisor") or "未填写"}
**完成日期**：{payload.get("complete_date") or "未填写"}

## 一、教材分析
本课《{topic}》在本单元中承担核心概念建构任务。教材按“情境引入—探究建构—迁移应用”组织，知识结构清晰，适合用任务驱动落实核心素养。

## 二、学情分析
{payload.get("student_context") or "学生已有一定基础知识，但迁移应用与概括表达能力不均衡，需要支架与分层任务。"}

## 三、教学目标
知识与技能：理解本课核心概念，并能用规范语言说明。
过程与方法：在探究与合作中完成证据收集、交流与建构。
情感态度价值观 / 学科核心素养：形成主动探究、合作交流的学习态度。

## 四、教学重点与难点
重点：建立核心概念之间的联系，并完成迁移应用。
难点：让不同基础的学生都能形成可观察的学习成果。
突破策略：学习单、追问支架、分层任务与及时反馈。

## 五、教学方法与策略
采用任务驱动、合作探究与即时评价相结合的策略，依据新课标强调学习过程与证据。

## 六、教学资源准备
课件、学习单、示例材料、评价量规。

## 七、教学过程设计
| 环节 | 教师活动 | 学生活动 | 设计意图 | 时间分配 |
| --- | --- | --- | --- | --- |
| 导入新课 | 出示情境问题，明确本节课核心任务 | 进入情境，提出已有认识 | 激活经验，定向学习 | 5分钟 |
| 新知探究 | 提供材料与关键问题，巡视指导 | 独立阅读或操作，记录发现 | 先学后教，形成证据 | 12分钟 |
| 合作学习 | 组织角色分工，追问理由 | 交流观点并形成小组结论 | 互学互补，深化理解 | 10分钟 |
| 巩固练习 | 出示分层练习并点评 | 完成基础/提高任务 | 检测目标达成 | 8分钟 |
| 课堂小结 | 引导学生结构化板书 | 用关键词回顾收获 | 建构知识网络 | 5分钟 |
| 作业布置 | 布置分层与实践作业 | 明确完成标准 | 延伸课堂学习 | 5分钟 |

## 八、板书设计
课题居中，左侧核心概念，右侧学习路径与关键词。

## 九、作业设计
基础巩固、实践应用、拓展探究三类分层作业，允许学生按学情选择。

## 十、教学评价设计
课堂观察、学习单、互评量规与教师即时反馈相结合。

## 十一、教学反思
亮点在于任务链条完整；需关注参与是否均衡、评价是否可观察。

**指导教师评语**

指导教师签字：__________    日期：____年__月__日"""

    if task == "note_report":
        titles = payload.get("titles", [])
        joined = "、".join(titles[:6]) or "本阶段跟岗笔记"
        period = payload.get("training_period") or "____年__月__日 至 ____年__月__日"
        sg = "/".join(x for x in [payload.get("subject"), payload.get("grade")] if x) or "未填写"
        return f"""# 跟岗研修总结报告

吴忠中学“组团帮扶”教师跟岗研修项目 · 泉州一中跟岗基地

> 说明：跟岗研修结束后撰写，全面总结研修期间的学习收获、反思感悟与返校行动计划。

**姓名**：{payload.get("teacher_name") or "未填写"}
**所在单位**：{payload.get("school_name") or "吴忠市吴忠中学"}
**学科/年级**：{sg}
**跟岗时间**：{period}
**跟岗基地**：{payload.get("training_base") or "福建省泉州第一中学"}
**指导教师**：{payload.get("advisor") or "未填写"}
**报告日期**：{payload.get("report_date") or "未填写"}

## 一、研修概况
本次跟岗在泉州一中开展，主要围绕听评课、集体备课、课堂教学改革与教研活动组织展开。本报告综合了以下笔记：{joined}。研修期间按计划参与课堂观察与研讨，了解基地校在课程实施、教研机制和课堂文化方面的做法。

## 二、主要收获
通过跟岗，进一步理解以学生为中心的课堂组织方式，看到任务驱动、评价前置和教研常态化如何落地。课堂教学改革方面，基地校更强调可观察的学习证据；课程体系建设方面，注意单元整体与校本资源衔接；教研活动方面，形成“问题—实践—再研讨”的闭环；学校管理经验方面，教研组有明确分工与成果沉淀机制。上述收获将作为返校改进的参照。

## 三、重点学习成果
结合所选笔记与个人教学设计实践，重点掌握了任务链设计、合作学习角色分工和即时评价方法，并尝试写入教学过程表的教师活动、学生活动与设计意图列，使设计可执行、可检测。

## 四、对比与反思
对照泉州一中实践，自身在课堂时间分配、学生表达支架和评价标准具体化方面仍有差距。原因在于以往更关注完成教学内容，对学习证据收集不够系统。跟岗笔记反映出需要把“学生做什么、产出什么”写进每一环节。

## 五、返校行动计划
回吴忠中学后，将在个人教学中连续试行任务驱动课堂；在教研组建设中组织一次基于课堂证据的研讨；在课程开发上整理一份单元学习单；在示范辐射上承担一次校内分享。目标明确、措施可在四周内启动。

## 六、意见与建议
建议项目继续保证导师跟课与集中研讨时间，适当增加学科对口交流，便于把听课所得更快转化为个人教学设计。

**学员签字**

日期：____年__月__日

**指导教师评语**

指导教师签字：__________    日期：____年__月__日"""

    if task == "question_answer":
        return """建议先把问题拆成“学习目标、任务情境、活动递进、评价证据”四个方面。先明确学生最终要形成什么可观察成果，再围绕成果设计连续任务。每个任务都要说明学生做什么、产出什么、教师如何判断完成质量。可以先在一个单元中小范围试行，记录不同层次学生的表现，再与教研组共同调整。\n\nAI回答仅作为教研参考，请结合学生实际情况和同伴教师意见判断。"""

    if task == "lesson_review":
        transcript = payload.get("transcript", "")
        summary = transcript[:120] if transcript else "当前未提供完整转写文本，以下为结构化示例分析。"
        return f"""# 听评课分析报告

## 一、课堂概况
{summary}

## 二、课堂结构观察
- 导入阶段能够快速建立学习情境。
- 核心活动以教师引导和学生任务为主。
- 课堂末尾具备总结或反馈环节。

## 三、课堂亮点
1. 教学目标与课堂任务基本一致。
2. 教师能够使用追问帮助学生说明理由。
3. 学习材料与任务之间具有较好的关联。

## 四、值得继续观察的问题
1. 不同学生获得表达机会是否均衡。
2. 小组活动的成果是否被充分利用。
3. 评价是否明确指向本节课目标。

## 五、改进建议
- 为学生提供更具体的表达支架。
- 在关键活动前明确成果标准。
- 减少重复性讲解，将时间留给学生展示和互评。

> 本分析主要依据上传材料和转写文本生成，仅作为听评课参考，不替代完整的人工课堂观察。"""

    if task == "assistant_chat":
        msg = str(payload.get("message") or "您好")
        file_name = str(payload.get("file_name") or "")
        prefix = f"已阅读「{file_name}」。" if file_name else ""
        return (
            f"{prefix}关于「{msg[:40]}」，可以先把目标拆成可观察的学习成果，再设计任务情境和评价证据。"
            "需要的话我可以继续帮你写活动步骤、课堂追问或评课观察要点。"
        )

    return "已生成内容。"
