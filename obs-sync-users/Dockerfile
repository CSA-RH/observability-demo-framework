FROM registry.redhat.io/ansible-automation-platform-24/ee-supported-rhel9:latest

RUN ansible-galaxy collection install \
    kubernetes.core

CMD ["/bin/bash"]