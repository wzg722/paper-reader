from django.conf import settings
from django.db import models


class GraphNode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='graph_nodes')
    node_type = models.CharField(max_length=20)  # paper / concept / related
    label = models.CharField(max_length=300)
    year = models.SmallIntegerField(null=True, blank=True)
    cites = models.IntegerField(null=True, blank=True)
    tags = models.CharField(max_length=255, blank=True, null=True)
    paper = models.ForeignKey('papers.Paper', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    read_status = models.BooleanField(default=False)
    team_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'graph_nodes'


class GraphEdge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='graph_edges')
    source_node = models.ForeignKey(GraphNode, on_delete=models.CASCADE, related_name='out_edges')
    target_node = models.ForeignKey(GraphNode, on_delete=models.CASCADE, related_name='in_edges')
    relation_type = models.CharField(max_length=20)  # cites / related / concept_of
    team_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'graph_edges'
