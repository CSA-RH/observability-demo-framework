from typing import Any, Dict

from operations.operation_store import DocumentOperationStore
from services.openshift.kube import ConfigMapJson, KubeApis
from settings import NamespaceLayout

OPERATIONS_CONFIGMAP = "obs-demo-fwk-operations"


class ConfigMapOperationStore(DocumentOperationStore):
    """Operations in a ConfigMap of the app namespace, so they survive orchestrator restarts."""

    def __init__(self, apis: KubeApis, layout: NamespaceLayout):
        self._store = ConfigMapJson(apis.core)
        self._layout = layout

    def _load(self) -> Dict[str, Any]:
        return self._store.load(OPERATIONS_CONFIGMAP, "operations", self._layout.app_namespace, default={})

    def _save(self, operations: Dict[str, Any]) -> None:
        self._store.save(OPERATIONS_CONFIGMAP, "operations", self._layout.app_namespace, operations)
