"""Domain services of the orchestrator (see `services.interfaces`)."""
from dataclasses import dataclass

from services.interfaces import (
    CapabilityService, MonitoringService, OperationStore, SimulationService, TenantService,
)


@dataclass
class Services:
    tenants: TenantService
    simulations: SimulationService
    monitoring: MonitoringService
    capabilities: CapabilityService
    operations: OperationStore


def build_mock_services(data_dir: str = "/tmp") -> Services:
    from services import mock

    files = mock.MockFiles(data_dir)
    monitoring = mock.MockMonitoringService(files)
    return Services(
        tenants=mock.MockTenantService(files),
        simulations=mock.MockSimulationService(files, monitoring),
        monitoring=monitoring,
        capabilities=mock.MockCapabilityService(),
        operations=mock.FileOperationStore(files),
    )


def build_openshift_services(settings, apis=None) -> Services:
    from services.openshift.capabilities import OpenShiftCapabilityService
    from services.openshift.kube import current_namespace, load_kube_apis
    from services.openshift.monitoring import OpenShiftMonitoringService
    from services.openshift.operations import ConfigMapOperationStore
    from services.openshift.simulations import OpenShiftSimulationService
    from services.openshift.tenants import OpenShiftTenantService
    from settings import NamespaceLayout

    apis = apis or load_kube_apis()
    layout = NamespaceLayout(settings, current_namespace)
    tenants = OpenShiftTenantService(apis, layout, settings)
    monitoring = OpenShiftMonitoringService(apis, layout)
    return Services(
        tenants=tenants,
        simulations=OpenShiftSimulationService(apis, layout, monitoring),
        monitoring=monitoring,
        capabilities=OpenShiftCapabilityService(apis, layout, settings, tenants),
        operations=ConfigMapOperationStore(apis, layout),
    )


def build_services(settings) -> Services:
    return build_mock_services() if settings.uses_mock_cluster else build_openshift_services(settings)
