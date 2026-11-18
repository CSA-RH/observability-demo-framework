{{/*
Fully-qualified image reference.
Usage: {{ include "obs.image" (dict "image" .Values.images.frontend "root" .) }}
*/}}
{{- define "obs.image" -}}
{{- $registry := .root.Values.images.registry | default (printf "image-registry.openshift-image-registry.svc:5000/%s" .root.Values.applicationNamespace) -}}
{{- printf "%s/%s:%s" (trimSuffix "/" $registry) .image.name (toString .image.tag) -}}
{{- end -}}

{{/*
`image.openshift.io/triggers` value for a Deployment container fed by an in-cluster ImageStreamTag:
a finished build rolls the Deployment out with the new image digest.
Usage: {{ include "obs.imageTrigger" (dict "image" .Values.images.frontend "container" "obs-console") }}
*/}}
{{- define "obs.imageTrigger" -}}
{{- $from := dict "kind" "ImageStreamTag" "name" (printf "%s:%s" .image.name (toString .image.tag)) -}}
{{- $fieldPath := printf "spec.template.spec.containers[?(@.name==\"%s\")].image" .container -}}
{{- list (dict "from" $from "fieldPath" $fieldPath) | toJson -}}
{{- end -}}
