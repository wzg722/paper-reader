from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from common.response import ok, fail
from accounts.serializers import UserSerializer
from .models import Team, TeamMember, TeamApplication


class TeamMemberSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='user', read_only=True)

    class Meta:
        model = TeamMember
        fields = ('id', 'user', 'user_info', 'role', 'joined_at')


class TeamSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    joined = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    members = TeamMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = (
            'id', 'name', 'description', 'owner', 'owner_name', 'avatar',
            'member_count', 'joined', 'is_owner', 'members', 'created_at',
        )
        read_only_fields = ('owner',)

    def get_joined(self, obj):
        req = self.context.get('request')
        if not req:
            return False
        return obj.members.filter(user=req.user).exists()

    def get_is_owner(self, obj):
        req = self.context.get('request')
        return bool(req and obj.owner_id == req.user.id)


class TeamApplicationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.CharField(source='user.avatar', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = TeamApplication
        fields = ('id', 'team', 'team_name', 'user', 'username', 'avatar', 'status', 'created_at')
        read_only_fields = ('user', 'status')


class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = TeamSerializer

    def get_queryset(self):
        return Team.objects.all().prefetch_related('members__user')

    def perform_create(self, serializer):
        team = serializer.save(owner=self.request.user)
        TeamMember.objects.create(team=team, user=self.request.user, role='owner')

    @action(detail=False, methods=['get'])
    def mine(self, request):
        ids = TeamMember.objects.filter(user=request.user).values_list('team_id', flat=True)
        qs = Team.objects.filter(id__in=ids)
        return ok(TeamSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        team = self.get_object()
        if team.members.filter(user=request.user).exists():
            return fail('已是成员')
        app, created = TeamApplication.objects.get_or_create(
            team=team, user=request.user, defaults={'status': 'pending'},
        )
        if not created and app.status == 'pending':
            return fail('申请已提交，请等待审批')
        if not created:
            app.status = 'pending'
            app.save(update_fields=['status'])
        return ok(TeamApplicationSerializer(app).data, message='申请已提交')

    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        team = self.get_object()
        if team.owner_id != request.user.id:
            return fail('仅队长可查看', status=403)
        qs = team.applications.filter(status='pending')
        return ok(TeamApplicationSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        team = self.get_object()
        if team.owner_id != request.user.id:
            return fail('仅队长可审批', status=403)
        app_id = request.data.get('application_id')
        action_name = request.data.get('action')  # approve / reject
        app = TeamApplication.objects.filter(id=app_id, team=team).first()
        if not app:
            return fail('申请不存在')
        if action_name == 'approve':
            app.status = 'approved'
            app.save(update_fields=['status'])
            TeamMember.objects.get_or_create(team=team, user=app.user, defaults={'role': 'member'})
            return ok(message='已通过')
        app.status = 'rejected'
        app.save(update_fields=['status'])
        return ok(message='已拒绝')

    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        team = self.get_object()
        if team.owner_id != request.user.id:
            return fail('仅队长可移除', status=403)
        uid = request.data.get('user_id')
        if uid == team.owner_id:
            return fail('不能移除队长')
        TeamMember.objects.filter(team=team, user_id=uid).delete()
        return ok(message='已移除')

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        team = self.get_object()
        if team.owner_id == request.user.id:
            return fail('队长请先转让或解散团队')
        TeamMember.objects.filter(team=team, user=request.user).delete()
        return ok(message='已退出')
