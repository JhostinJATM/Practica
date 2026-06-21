from django.db import models


class AuditoriaRegistro(models.Model):
    ACCIONES = [
        ('confirmar', 'Confirmar'),
        ('corregir', 'Corregir'),
        ('descalificar', 'Descalificar'),
    ]

    registro_tiempo = models.ForeignKey(
        'RegistroTiempo',
        on_delete=models.CASCADE,
        related_name='auditorias',
        verbose_name="Registro de tiempo"
    )
    juez = models.ForeignKey(
        'Juez',
        on_delete=models.CASCADE,
        related_name='auditorias',
        verbose_name="Juez"
    )
    accion = models.CharField(
        max_length=15,
        choices=ACCIONES,
        verbose_name="Acción"
    )
    valor_anterior = models.JSONField(
        verbose_name="Valor anterior"
    )
    valor_nuevo = models.JSONField(
        verbose_name="Valor nuevo"
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )

    class Meta:
        verbose_name = "Auditoría de Registro"
        verbose_name_plural = "Auditorías de Registros"
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['registro_tiempo', 'creado_en']),
            models.Index(fields=['juez', 'creado_en']),
        ]

    def __str__(self):
        return f"Auditoría {self.accion} - Registro {self.registro_tiempo_id} por Juez {self.juez_id}"
