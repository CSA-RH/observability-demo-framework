{{/*
Fully-qualified image reference.
Usage: {{ include "obs.image" (dict "image" .Values.images.frontend "root" .) }}
*/}}
{{- define "obs.image" -}}
{{- $registry := .root.Values.images.registry | default (printf "image-registry.openshift-image-registry.svc:5000/%s" .root.Values.applicationNamespace) -}}
{{- printf "%s/%s:%s" (trimSuffix "/" $registry) .image.name (toString .image.tag) -}}
{{- end -}}
