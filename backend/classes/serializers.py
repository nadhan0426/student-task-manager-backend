from rest_framework import serializers
from classes.models import Classroom, ClassEnrollment, ClassJoinRequest
from accounts.serializers import UserSerializer

class ClassroomSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ('id', 'name', 'section', 'academic_year', 'description', 'teacher', 'code', 'is_joining_enabled', 'student_count', 'created_at')
        read_only_fields = ('id', 'teacher', 'code', 'created_at')

    def create(self, validated_data):
        if not validated_data.get('section'):
            validated_data['section'] = 'A'
        if not validated_data.get('academic_year'):
            validated_data['academic_year'] = '2026-2027'
        if 'is_joining_enabled' not in validated_data:
            validated_data['is_joining_enabled'] = True
        return super().create(validated_data)

    def get_student_count(self, obj):
        return obj.enrollments.filter(is_active=True).count()

class ClassEnrollmentSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    classroom = ClassroomSerializer(read_only=True)

    class Meta:
        model = ClassEnrollment
        fields = ('id', 'classroom', 'student', 'enrolled_at', 'is_active')

class ClassJoinRequestSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    classroom = ClassroomSerializer(read_only=True)

    class Meta:
        model = ClassJoinRequest
        fields = ('id', 'classroom', 'student', 'status', 'requested_at', 'reviewed_at')
        read_only_fields = ('id', 'classroom', 'student', 'requested_at', 'reviewed_at')
