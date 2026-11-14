from rest_framework import serializers
from submissions.models import TaskSubmission, SubmissionImage, SubmissionReview, ReviewDecision
from tasks.serializers import TaskAssignmentSerializer
from accounts.serializers import UserSerializer

class SubmissionImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = SubmissionImage
        fields = ('id', 'image', 'image_url', 'uploaded_at')
        read_only_fields = ('id', 'uploaded_at')

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class SubmissionReviewSerializer(serializers.ModelSerializer):
    reviewer = UserSerializer(read_only=True)

    class Meta:
        model = SubmissionReview
        fields = ('id', 'submission', 'reviewer', 'decision', 'feedback', 'reviewed_at')
        read_only_fields = ('id', 'reviewer', 'reviewed_at')

class TaskSubmissionSerializer(serializers.ModelSerializer):
    images = SubmissionImageSerializer(many=True, read_only=True)
    reviews = SubmissionReviewSerializer(many=True, read_only=True)
    assignment_info = TaskAssignmentSerializer(source='assignment', read_only=True)

    class Meta:
        model = TaskSubmission
        fields = ('id', 'assignment', 'assignment_info', 'version', 'student_comments', 'images', 'reviews', 'submitted_at', 'is_latest')
        read_only_fields = ('id', 'version', 'submitted_at', 'is_latest')
