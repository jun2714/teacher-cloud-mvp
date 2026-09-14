from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from services.ai import AIServiceError, generate_text
from services.notices import push_notice
from .models import Question, Answer
from .serializers import QuestionSerializer, AnswerSerializer

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.select_related("author", "author__teacher_profile").prefetch_related(
        "liked_by", "answers", "answers__liked_by", "answers__author", "answers__author__teacher_profile"
    )
    serializer_class = QuestionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        scope = self.request.query_params.get("scope")
        user = self.request.user
        if not user.is_authenticated:
            return qs
        if scope == "mine":
            return qs.filter(author=user)
        if scope == "answered":
            return qs.filter(answers__author=user, answers__answer_type="teacher").distinct()
        return qs

    def perform_create(self, serializer):
        question = serializer.save(author=self.request.user)
        if question.ask_ai:
            try:
                content = generate_text("question_answer", {
                    "title": question.title,
                    "content": question.content,
                    "subject": question.subject,
                    "grade": question.grade,
                    "tags": question.tags,
                })
                Answer.objects.create(question=question, answer_type="ai", content=content)
                question.status = "discussing"
                question.save(update_fields=["status"])
            except AIServiceError:
                Answer.objects.create(
                    question=question,
                    answer_type="ai",
                    content="AI 参考回答暂时无法生成，请稍后重试或直接邀请同事作答。",
                )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author_id != request.user.id:
            return Response({"detail": "只能修改自己的问题"}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "只能删除自己的问题"}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def answer(self, request, pk=None):
        question = self.get_object()
        content = (request.data.get("content") or "").strip()
        if not content:
            return Response({"detail": "回答内容不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        answer = Answer.objects.create(question=question, author=request.user, answer_type="teacher", content=content)
        if question.status == "pending":
            question.status = "discussing"
            question.save(update_fields=["status"])
        if question.author_id != request.user.id:
            push_notice(question.author, "community", "你的问题有了新回答", question.title, f"/questions/{question.id}")
        return Response(AnswerSerializer(answer, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="toggle-like")
    def toggle_like(self, request, pk=None):
        question = self.get_object()
        if question.liked_by.filter(id=request.user.id).exists():
            question.liked_by.remove(request.user)
            liked = False
        else:
            question.liked_by.add(request.user)
            liked = True
            if question.author_id != request.user.id:
                push_notice(question.author, "community", "有人赞同了你的问题", question.title, f"/questions/{question.id}")
        return Response({"liked": liked, "like_count": question.liked_by.count()})

    @action(detail=True, methods=["post"], url_path="mark-solved")
    def mark_solved(self, request, pk=None):
        question = self.get_object()
        if question.author_id != request.user.id:
            return Response({"detail": "只有提问者可以标记已解答"}, status=status.HTTP_403_FORBIDDEN)
        answer_id = request.data.get("answer_id")
        if answer_id:
            answer = question.answers.filter(id=answer_id).first()
            if not answer:
                return Response({"detail": "答案不存在"}, status=status.HTTP_400_BAD_REQUEST)
            question.answers.update(is_accepted=False)
            answer.is_accepted = True
            answer.save(update_fields=["is_accepted"])
            question.accepted_answer = answer
        question.status = "solved"
        question.save(update_fields=["status", "accepted_answer"])
        return Response(self.get_serializer(question).data)

class AnswerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Answer.objects.select_related("author", "question").prefetch_related("liked_by")
    serializer_class = AnswerSerializer

    @action(detail=True, methods=["post"], url_path="toggle-like")
    def toggle_like(self, request, pk=None):
        answer = self.get_object()
        if answer.liked_by.filter(id=request.user.id).exists():
            answer.liked_by.remove(request.user)
            liked = False
        else:
            answer.liked_by.add(request.user)
            liked = True
            if answer.author_id and answer.author_id != request.user.id:
                push_notice(answer.author, "community", "有人觉得你的回答有帮助", answer.question.title, f"/questions/{answer.question_id}")
        return Response({"liked": liked, "like_count": answer.liked_by.count()})
