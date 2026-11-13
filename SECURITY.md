# Política de seguridad

## Alcance

Este repositorio contiene una interfaz web y un puente local para comunicación USB/serie con ECUs. El puente no debe exponerse a Internet ni a redes no confiables.

## Configuración segura

El servidor escucha en `127.0.0.1` por defecto. Solo debe configurarse `DCTUNER_HOST` a una dirección de red concreta cuando se necesite acceso desde otro equipo, y únicamente detrás de una red confiable y controles de firewall.

No se deben añadir credenciales, claves privadas, tokens ni datos de ECU a este repositorio. Los registros exportados pueden contener información sensible del vehículo y deben mantenerse fuera del control de versiones.

## Reportar vulnerabilidades

No publiques una vulnerabilidad como issue. Abre un aviso privado de seguridad en GitHub desde la pestaña **Security** del repositorio, incluyendo pasos reproducibles, impacto, versión afectada y una propuesta de corrección si está disponible.

Las correcciones deben conservar la separación entre la interfaz web pública y el puente local que tiene acceso al puerto serie.
