Create some users in Keycloak in the CSA realm

```bash
podman run -it \
    -e ANSIBLE_DEBUG=true \
    --rm \
    -v $(pwd):/runner \
    registry.redhat.io/ansible-automation-platform-24/ee-supported-rhel9 \
    bash -c "ansible-galaxy collection install middleware_automation.keycloak && ansible-playbook playbook-users.yml"
```