from rest_framework import serializers
from classes.models import Classroom, ClassEnrollment
from accounts.serializers import UserSerializer

class ClassroomSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ('id', 'name', 'description', 'teacher', 'code', 'student_count', 'created_at')
        read_only_fields = ('id', 'teacher', 'code', 'created_at')

    def get_student_count(self, obj):
        return obj.enrollments.filter(is_active=True).count()

class ClassEnrollmentSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    classroom = ClassroomSerializer(read_only=True)

    class Meta:
        model = ClassEnrollment
        fields = ('id', 'classroom', 'student', 'enrolled_at', 'is_active')
