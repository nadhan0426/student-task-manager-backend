from rest_framework import serializers
from credits.models import CreditTransaction
from accounts.serializers import UserSerializer
from tasks.serializers import TaskAssignmentSerializer

class CreditTransactionSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    assignment_info = TaskAssignmentSerializer(source='assignment', read_only=True)

    class Meta:
        model = CreditTransaction
        fields = (
            'id', 'assignment', 'assignment_info', 'student',
            'amount', 'transaction_type', 'created_by', 'reason', 'created_at'
        )
        read_only_fields = ('id', 'student', 'created_by', 'created_at')
