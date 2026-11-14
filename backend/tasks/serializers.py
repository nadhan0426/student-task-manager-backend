from rest_framework import serializers
from tasks.models import Task, TaskAssignment, TaskPriority, AssignmentStatus
from classes.serializers import ClassroomSerializer
from accounts.serializers import UserSerializer

class TaskSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    classroom_info = ClassroomSerializer(source='classroom', read_only=True)
    assigned_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'instructions', 'category',
            'priority', 'max_credit_points', 'due_date', 'created_by',
            'classroom', 'classroom_info', 'is_archived', 'assigned_count',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def get_assigned_count(self, obj):
        return obj.assignments.count()

class TaskAssignmentSerializer(serializers.ModelSerializer):
    task = TaskSerializer(read_only=True)
    student = UserSerializer(read_only=True)

    class Meta:
        model = TaskAssignment
        fields = (
            'id', 'task', 'student', 'status',
            'assigned_at', 'started_at', 'completed_at', 'earned_credits'
        )
        read_only_fields = ('id', 'task', 'student', 'assigned_at', 'earned_credits')

class TaskCreateSerializer(serializers.ModelSerializer):
    student_ids = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True)
    assign_to_class = serializers.BooleanField(default=False, write_only=True)

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'instructions', 'category',
            'priority', 'max_credit_points', 'due_date', 'classroom',
            'student_ids', 'assign_to_class'
        )
