# CamaleónDJ - Project Plan

> Documento maestro del proyecto.
>
> Este archivo es la referencia principal para continuar el desarrollo de CamaleónDJ. Si el contexto de una conversación se pierde o es necesario iniciar un nuevo chat, este documento debe leerse antes de continuar.

---

# Estado del proyecto

**Proyecto:** CamaleónDJ

**Estado:** En desarrollo

**Versión interna:** 0.9

**Etapa actual:**
Consolidación de arquitectura.

**Última actualización:**
11/03/2026

---

# Visión del proyecto

CamaleónDJ es un bot de Discord orientado a ofrecer una experiencia musical completa, con una arquitectura modular, mantenible y preparada para crecer.

Los objetivos principales del proyecto son:

- estabilidad;
- claridad del código;
- facilidad para agregar nuevas funcionalidades;
- evitar duplicaciones;
- mantener una arquitectura limpia;
- facilitar el mantenimiento a largo plazo.

---

# Reglas de desarrollo

Estas reglas tienen prioridad durante todo el proyecto.

1. El roadmap no se modifica mientras una etapa esté en progreso.

2. Siempre existe una única tarea activa.

3. No comenzar una nueva tarea sin terminar la anterior.

4. Cada cambio importante debe dejar el bot funcionando.

5. Toda mejora nueva pasa primero al Backlog.

6. Refactorizar únicamente cuando elimine duplicaciones o simplifique realmente la arquitectura.

7. Evitar refactorizaciones masivas.

8. Probar el bot después de cada cambio importante.

9. Si durante una conversación se pierde el contexto, este documento pasa a ser la fuente principal del proyecto.

10. Antes de iniciar una nueva sesión de desarrollo se debe revisar este documento.

---

# Arquitectura actual

MusicPlayer

├── MusicQueue

├── MusicCache

├── Song

├── YoutubeService

├── SpotifyService

├── MediaResolver

├── MediaLoader

└── Discord UI

---

# Roadmap

## Etapa 1 — Consolidación de arquitectura (ACTUAL)

Estado: En progreso

- [ ] Integrar completamente MusicPlayer.
- [ ] Eliminar QueueManager.
- [ ] Eliminar prefetch_cache.
- [ ] Centralizar el estado del reproductor.
- [ ] Probar toda la reproducción.

---

## Etapa 2 — Organización del proyecto

Pendiente.

- [ ] Crear Cogs.
- [ ] Separar comandos.
- [ ] Separar eventos.
- [ ] Separar interfaz (Views).

---

## Etapa 3 — Funcionalidades

Pendiente.

- [ ] Sistema Help.
- [ ] Embed automático en #⭐comandos-dj.
- [ ] Loop.
- [ ] LoopQueue.
- [ ] Radio.
- [ ] Autoplay.
- [ ] Favoritos.
- [ ] Historial.
- [ ] Letras.
- [ ] Mejoras de experiencia de usuario.

---

## Etapa 4 — Escalabilidad

Pendiente.

- [ ] Soporte para múltiples servidores.
- [ ] Configuración por servidor.
- [ ] Persistencia.
- [ ] Base de datos.
- [ ] Estadísticas.

---

# Tarea activa

Integrar completamente MusicPlayer para que sea el núcleo del bot.

---

# Próximo paso

Eliminar QueueManager migrando toda la gestión de la cola hacia MusicPlayer y MusicQueue.

---

# Backlog

Ideas aprobadas para el futuro.

- Radio inteligente.
- Autoplay avanzado.
- Sistema de favoritos.
- Historial de reproducción.
- Letras de canciones.
- Mejoras visuales del panel.
- Estadísticas de uso.
- Dashboard web.
- Sistema de configuración.
- Multi-servidor.
- Otras mejoras que surjan durante el desarrollo.

---

# Decisiones de arquitectura

### DEC-001

Song es el único modelo para representar canciones.

Estado:
Adoptada.

---

### DEC-002

MusicPlayer será el núcleo del bot.

Estado:
En progreso.

---

### DEC-003

No utilizar diccionarios para representar canciones.

Estado:
En implementación.

---

### DEC-004

El roadmap sólo puede modificarse al finalizar una etapa.

Estado:
Adoptada.

---

# Historial del proyecto

## Arquitectura

- Se creó MediaResolver.
- Se creó MediaLoader.
- Se creó QueueManager.
- Se creó PlayerState.
- Se creó MusicPlayer.
- Se creó MusicQueue.
- Se creó MusicCache.
- Se creó Song.

## Funcionalidades

- Reproducción desde YouTube.
- Reproducción desde Spotify.
- Playlists de YouTube.
- Playlists de Spotify.
- Cola de reproducción.
- Shuffle.
- Move.
- Jump.
- Remove.
- Volumen.
- Panel de reproducción.
- Controles mediante botones.

---

# Notas para futuras sesiones

Antes de comenzar una nueva sesión:

1. Leer este documento completo.

2. Verificar la Tarea Activa.

3. Continuar desde el Próximo Paso.

4. No modificar el roadmap hasta finalizar la etapa actual.

5. Actualizar este documento al finalizar cada etapa importante.