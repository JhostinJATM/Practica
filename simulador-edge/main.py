import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import os
from datetime import datetime


def _cargar_env():
    """Carga variables de entorno desde archivo .env si existe."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.isfile(env_path):
        return
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_cargar_env()

from generador import GeneradorEventos
from cliente_http import ClienteHTTP
from persistencia import guardar_registro, obtener_pendientes, obtener_pendientes_con_record_id, marcar_enviado, incrementar_intentos


class SimuladorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Simulador Edge - RASC UNL Vision')
        self.root.geometry('800x650')
        self.root.resizable(True, True)

        self.generador = GeneradorEventos()
        self.cliente = ClienteHTTP(log_callback=self.agregar_log)
        self.modo_automatico = False
        self.hilo_auto = None
        self.num_dorsales = 5

        self._construir_interfaz()
        self._actualizar_estado_conexion()
        self._iniciar_verificador_pendientes()

    def _construir_interfaz(self):
        frame_principal = ttk.Frame(self.root, padding=10)
        frame_principal.pack(fill=tk.BOTH, expand=True)

        # Fila de estado
        frame_estado = ttk.LabelFrame(frame_principal, text='Estado', padding=5)
        frame_estado.pack(fill=tk.X, pady=(0, 10))

        self.lbl_conexion = ttk.Label(frame_estado, text='Conectando...', foreground='orange')
        self.lbl_conexion.pack(side=tk.LEFT, padx=10)

        self.lbl_competencia = ttk.Label(frame_estado, text='Competencia: --')
        self.lbl_competencia.pack(side=tk.LEFT, padx=10)

        self.lbl_token = ttk.Label(frame_estado, text=f'Token: {self.cliente.token[:8]}...' if self.cliente.token else 'Token: NO CONFIGURADO')
        self.lbl_token.pack(side=tk.RIGHT, padx=10)

        # Panel de control
        frame_control = ttk.LabelFrame(frame_principal, text='Control', padding=5)
        frame_control.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame_control, text='Dorsales a usar:').pack(side=tk.LEFT, padx=5)
        self.spin_dorsales = ttk.Spinbox(frame_control, from_=1, to=100, width=5)
        self.spin_dorsales.set(5)
        self.spin_dorsales.pack(side=tk.LEFT, padx=5)

        self.btn_auto = ttk.Button(frame_control, text='Iniciar Modo Automatico', command=self._toggle_automatico)
        self.btn_auto.pack(side=tk.LEFT, padx=10)

        ttk.Label(frame_control, text='Intervalo (s):').pack(side=tk.LEFT, padx=5)
        self.spin_intervalo = ttk.Spinbox(frame_control, from_=1, to=60, width=3)
        self.spin_intervalo.set(3)
        self.spin_intervalo.pack(side=tk.LEFT, padx=5)

        # Panel manual
        frame_manual = ttk.LabelFrame(frame_principal, text='Envio Manual', padding=5)
        frame_manual.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame_manual, text='Dorsal:').pack(side=tk.LEFT, padx=5)
        self.entry_dorsal = ttk.Entry(frame_manual, width=8)
        self.entry_dorsal.pack(side=tk.LEFT, padx=5)
        self.entry_dorsal.insert(0, '1')

        ttk.Label(frame_manual, text='Tiempo (ms):').pack(side=tk.LEFT, padx=5)
        self.entry_tiempo = ttk.Entry(frame_manual, width=10)
        self.entry_tiempo.pack(side=tk.LEFT, padx=5)
        self.entry_tiempo.insert(0, '60000')

        ttk.Label(frame_manual, text='Confianza OCR:').pack(side=tk.LEFT, padx=5)
        self.entry_confianza = ttk.Entry(frame_manual, width=8)
        self.entry_confianza.pack(side=tk.LEFT, padx=5)
        self.entry_confianza.insert(0, '98.5')

        self.btn_enviar = ttk.Button(frame_manual, text='Enviar', command=self._enviar_manual)
        self.btn_enviar.pack(side=tk.LEFT, padx=10)

        # Log
        frame_log = ttk.LabelFrame(frame_principal, text='Log', padding=5)
        frame_log.pack(fill=tk.BOTH, expand=True)

        self.txt_log = scrolledtext.ScrolledText(frame_log, height=15, state='disabled')
        self.txt_log.pack(fill=tk.BOTH, expand=True)

    def _actualizar_estado_conexion(self):
        conectado = self.cliente.verificar_conexion()
        if conectado:
            self.lbl_conexion.config(text='Conectado', foreground='green')
            nombre = self.cliente.obtener_competencia()
            self.lbl_competencia.config(text=f'Competencia: {nombre}')
        else:
            self.lbl_conexion.config(text='Desconectado', foreground='red')
            self.lbl_competencia.config(text='Competencia: --')

        self.root.after(5000, self._actualizar_estado_conexion)

    def agregar_log(self, mensaje):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.txt_log.config(state='normal')
        self.txt_log.insert(tk.END, f'[{timestamp}] {mensaje}\n')
        self.txt_log.see(tk.END)
        self.txt_log.config(state='disabled')

    def _toggle_automatico(self):
        if self.modo_automatico:
            self.modo_automatico = False
            self.btn_auto.config(text='Iniciar Modo Automatico')
            self.agregar_log('Modo automatico DETENIDO')
        else:
            self.modo_automatico = True
            self.btn_auto.config(text='Detener Modo Automatico')
            self.agregar_log('Modo automatico INICIADO')
            self.hilo_auto = threading.Thread(target=self._loop_automatico, daemon=True)
            self.hilo_auto.start()

    def _loop_automatico(self):
        intervalo = int(self.spin_intervalo.get())
        num_dorsales = int(self.spin_dorsales.get())

        while self.modo_automatico:
            for _ in range(num_dorsales):
                if not self.modo_automatico:
                    break
                evento = self.generador.generar_evento()
                self._enviar_evento(evento)
                time.sleep(0.3)
            time.sleep(intervalo)

    def _enviar_manual(self):
        try:
            dorsal = int(self.entry_dorsal.get())
            tiempo_ms = int(self.entry_tiempo.get())
            confianza = float(self.entry_confianza.get())
            evento = self.generador.generar_manual(dorsal, tiempo_ms, confianza)
            self._enviar_evento(evento)
        except ValueError as e:
            self.agregar_log(f'Error: Datos invalidos - {e}')

    def _enviar_evento(self, evento):
        dorsal = evento['dorsal']
        tiempo_ms = evento['tiempo_ms']
        confianza = evento['confianza_ocr']

        exito, data = self.cliente.enviar_registro(dorsal, tiempo_ms, confianza)

        if exito:
            estado = data.get('estado', '?')
            record_id = data.get('record_id')
            self.agregar_log(f'Dorsal {dorsal} | {tiempo_ms}ms | OCR {confianza}% | {estado}')
            # Si quedo pendiente de validacion, guardar localmente para dar seguimiento
            if estado == 'pendiente' and record_id:
                guardar_registro(dorsal, tiempo_ms, confianza, record_id)
        else:
            guardar_registro(dorsal, tiempo_ms, confianza)
            self.agregar_log(f'[PENDIENTE] Dorsal {dorsal} | {tiempo_ms}ms | OCR {confianza}% - Guardado localmente')

    def iniciar(self):
        self.agregar_log('Simulador Edge iniciado')
        self.agregar_log(f'Backend: {self.cliente.backend_url}')
        self.root.mainloop()

    def _iniciar_verificador_pendientes(self):
        """Hilo en segundo plano que verifica el estado de registros pendientes."""
        self._hilo_verificador = threading.Thread(target=self._verificar_pendientes, daemon=True)
        self._hilo_verificador.start()

    def _verificar_pendientes(self):
        """Verifica periodicamente registros pendientes contra el servidor."""
        while True:
            time.sleep(10)  # Verificar cada 10 segundos
            try:
                pendientes = obtener_pendientes_con_record_id()
                for p in pendientes:
                    exito, data = self.cliente.verificar_estado_registro(p['record_id'])
                    if not exito:
                        continue
                    estado = data.get('estado', '')
                    if estado in ('validado', 'corregido'):
                        marcar_enviado(p['id'])
                        self.agregar_log(f'[VALIDADO] Registro {p["record_id"][:8]}... confirmado por juez ({estado})')
                    elif estado == 'descalificado':
                        marcar_enviado(p['id'])
                        motivo = data.get('motivo_descalificacion', 'sin motivo')
                        self.agregar_log(f'[DESCALIFICADO] Registro {p["record_id"][:8]}... descalificado: {motivo}')
            except Exception:
                pass


if __name__ == '__main__':
    app = SimuladorApp()
    app.iniciar()
