# Manual de Usuario del Asistente NORMATIVA-TG UTS
## Guía Práctica de Consulta para Estudiantes, Docentes y Administradores
**Código Institucional:** F-DC-124 / F-DC-125  
**Institución:** Unidades Tecnológicas de Santander (UTS)  
**Fecha de consolidación:** Noviembre de 2026  
**Versión:** 1.0 (Entrega Técnica Final)  

---

## 1. Introducción y Propósito del Asistente

El asistente inteligente **NORMATIVA-TG UTS** es una herramienta web de apoyo académico desarrollada para facilitar la consulta rápida, precisa y fundamentada del **Reglamento de Trabajo de Grado** de las Unidades Tecnológicas de Santander.

A través de una interfaz de chat moderna e intuitiva, los estudiantes de programas tecnológicos y universitarios, directores de proyecto, evaluadores y coordinadores pueden formular preguntas en su lenguaje natural cotidiano y recibir respuestas sustentadas en los artículos oficiales vigentes.

> [!IMPORTANT]
> **Carácter Estrictamente Orientativo (Directriz F-DC-124):**  
> Las respuestas brindadas por este asistente inteligente tienen un propósito exclusivamente informativo y orientativo. El sistema **no emite actos administrativos ni decisiones oficiales vinculantes**. Para solicitudes formales, prórrogas oficiales, sustentaciones o apelaciones, el usuario debe dirigirse a la Secretaría Académica o al Comité de Trabajo de Grado de su respectivo programa.

---

## 2. Acceso a la Plataforma Web

La aplicación es accesible desde cualquier navegador web moderno (Google Chrome, Mozilla Firefox, Microsoft Edge o Safari) ingresando a la dirección local asignada:

- **Dirección pública del Chat Normativo:** `http://localhost:5173`
- **Dirección de Administración del Corpus:** `http://localhost:5173/admin`

---

## 3. Guía de Uso del Chat Normativo (Público)

### 3.1. Elementos de la Interfaz Principal

```text
+---------------------------------------------------------------------------------------+
|  [UTS Logo]  NORMATIVA-TG UTS  (Prototipo F-DC-124)     [● Activo: Reg. 2019] [Admin] |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|   ¡Bienvenido a NORMATIVA-TG UTS!                                                     |
|   Asistente inteligente de consulta sobre el Reglamento de Trabajo de Grado.          |
|                                                                                       |
|   [ Preguntas Sugeridas: ]                                                            |
|   [ "¿Cuáles son las modalidades?" ] [ "¿Cuánto tiempo tengo?" ] [ "¿Puedo prórroga?" ]|
|                                                                                       |
|   ---------------------------------------------------------------------------------   |
|   Usuario: ¿Cuáles son las modalidades de Trabajo de Grado?                           |
|                                                                                       |
|   Asistente: Las modalidades contempladas en el reglamento son seis:                  |
|   1. Proyecto de Investigación                                                        |
|   2. Desarrollo Tecnológico                                                           |
|   3. Monografía                                                                       |
|   4. Seminario                                                                        |
|   5. Práctica (Nivel Técnico Profesional)                                             |
|   6. Emprendimiento                                                                   |
|                                                                                       |
|   [ Citas Normativas Oficiales: ]                                                     |
|   ┌───────────────────────────────────────────────────────────────────────────────┐   |
|   │ Art. 8 - Capítulo III: DE LAS MODALIDADES DE TRABAJO DE GRADO (pág. 4)        │   |
|   │ "El estudiante de las Unidades Tecnológicas de Santander puede desarrollar..."│   |
|   │ [Ver en PDF Original]                                                         │   |
|   └───────────────────────────────────────────────────────────────────────────────┘   |
|                                                                                       |
|   Aviso: Esta respuesta es orientativa y se basa en el reglamento indexado.           |
|   ---------------------------------------------------------------------------------   |
|   [ Escriba su consulta sobre el reglamento...                              ] [Enviar]|
+---------------------------------------------------------------------------------------+
```

1. **Barra Superior (Navbar):**  
   - Logotipo institucional y título del prototipo.
   - **Indicador de Normativa Activa:** Muestra una esfera verde titilante y el nombre del reglamento que está respondiendo las consultas (por ejemplo: `Reglamento de Trabajo de Grado 2019 (2019)`).
   - Enlace de acceso a la sección de **Administración**.
2. **Área de Conversación:**  
   - Mensaje de bienvenida con sugerencias rápidas de consulta.
   - Historial de preguntas formuladas y respuestas generadas.
3. **Caja de Entrada de Texto:**  
   - Campo para escribir preguntas con límite de 3 a 1.000 caracteres.
   - Botón de envío habilitado con retroalimentación animada de carga mientras el modelo local procesa la respuesta.

---

### 3.2. Cómo Formular Preguntas Efectivas
Para obtener las respuestas más precisas, siga estas recomendaciones:
- **Sea específico con su situación académica:** Si pertenece a un programa técnico, indíquelo: *"Soy de tecnología, ¿puedo hacer monografía?"*.
- **Consulte plazos y trámites concretos:** *"¿Cuánto tiempo tengo para entregar el informe final tras la aprobación de la propuesta?"*.
- **Pregunte por causales y excepciones:** *"¿En qué casos me pueden reprobar el trabajo de grado?"*, *"¿La modalidad de seminario admite prórroga?"*.

---

### 3.3. Interpretación de Respuestas y Citas Estructuradas

Cada respuesta sustantiva del asistente se compone de tres secciones visuales:

1. **Síntesis Explicativa:**  
   Texto redactado en lenguaje claro que resume la disposición reglamentaria aplicable.
2. **Tarjetas de Cita Normativa Deterministas:**  
   Debajo de la respuesta, el sistema presenta las tarjetas con las fuentes exactas recuperadas. Cada tarjeta detalla:
   - Número de Capítulo y su título temático oficial.
   - Número de Artículo, Parágrafo o Inciso específico.
   - Folio o página exacta en el documento PDF físico (ej: `págs. 4-4`).
   - Fragmento literal del texto extraído del reglamento.
3. **Botón "Ver en PDF":**  
   Al presionar este botón, se abre un visor modal que carga directamente el archivo PDF oficial en la página exacta donde se encuentra el artículo citado, permitiendo al usuario verificar con sus propios ojos la autenticidad de la disposición.

---

### 3.4. Casos Especiales de Respuesta

#### A. Consultas Ambiguas o Parciales
Si usted formula una pregunta general como *"¿Cuántos días tengo para el informe?"*, el asistente no inventará un número absoluto; le aclarará que existen 180 días calendario para finalizar todo el trabajo de grado, que no puede entregarse antes de 3 meses, y le formulará una pregunta aclaratoria:  
> *«¿A qué modalidad pertenece su proyecto o en qué fase de desarrollo se encuentra?»*

#### B. Preguntas Sin Evidencia en el Reglamento
Si pregunta por un dato operativo o financiero que no forma parte del texto normativo (por ejemplo: *"¿Cuánto vale el seminario de grado este año en pesos?"* o *"¿Cuál es el correo del comité de grado de electromecánica?"*):  
- El sistema responderá que el reglamento alude a derechos pecuniarios o comités de programa, pero **no inventará un precio en pesos ni un correo no registrado**.
- Le sugerirá consultar directamente a la Tesorería o a la Coordinación Académica respectiva.

#### C. Preguntas Fuera de Alcance
Si formula una pregunta totalmente ajena a las normas de las UTS (como recetas de cocina, clima o instalación de software):  
- El sistema activará el estado de **Abstención Fuera de Alcance** (`abstained: true`), indicando cortésmente que su labor se limita a resolver dudas sobre el Reglamento de Trabajo de Grado institucional.

---

## 4. Guía de Uso del Panel Administrativo (Administradores)

### 4.1. Inicio de Sesión Administrativo
1. Diríjase a `http://localhost:5173/admin/login`.
2. Ingrese la clave de administración (`ADMIN_API_KEY`, definida por defecto como `dev-admin-secret-key` en entornos locales).
3. Presione **Iniciar Sesión**. La aplicación establecerá una cookie segura HttpOnly y lo redirigirá al Dashboard.

### 4.2. Dashboard de Control Normativo
El panel administrativo presenta cuatro tarjetas de estadísticas en tiempo real:
- **Reglamentos Registrados:** Total de versiones normativas en base de datos.
- **Versión Activa Global:** Nombre del reglamento que actualmente responde las consultas públicas.
- **Total Chunks en Base Vectorial:** Cantidad de fragmentos indexados en Qdrant.
- **Consultas Auditadas:** Total de trazas registradas en la tabla de auditoría.

---

### 4.3. Carga e Ingestión de un Nuevo Reglamento (PDF)
Cuando el Consejo Directivo de las UTS apruebe una reforma o un nuevo reglamento:
1. En el Dashboard administrativo, haga clic en el botón verde **«Cargar Nueva Normativa»**.
2. Complete los campos del formulario:
   - **Nombre de la Versión:** Ej. *Reglamento de Trabajo de Grado 2026*.
   - **Número de Acuerdo:** Ej. *Acuerdo No. 01-045*.
   - **Año:** Ej. *2026*.
   - **Fecha de Expedición:** Seleccione en el calendario la fecha formal del acta.
   - **Estado de Vigencia:** Seleccione *Vigente*, *Derogado* o *En Revisión*.
   - **Archivo PDF:** Seleccione el archivo oficial en su disco duro.
3. Presione **«Subir y Procesar»**.
4. El backend guardará el archivo en `data/pdfs/`, ejecutará el pipeline de extracción (OCR si es escaneado), limpiará encabezados y creará los chunks vectoriales.

---

### 4.4. Auditoría OCR y Aprobación de Revisión Humana
Antes de activar una normativa, el administrador puede auditar la calidad del procesamiento:
1. Ubique el reglamento en la tabla y haga clic en **«Ver Auditoría»**.
2. El modal presentará:
   - Confianza media global del OCR (ej: `91.71%`).
   - Total de páginas sometidas a OCR.
   - Alertas de páginas con baja confianza (si existen páginas bajo el 75%).
   - Reparaciones automáticas de artículos (ej: Artículo 1 corregido por secuencia).
   - Desglose de líneas de encabezado y pie eliminadas.
3. Si el resultado es satisfactorio, presione **«Aprobar Revisión»**. El estado cambiará a `APROBADO`.

---

### 4.5. Activación de la Versión en Caliente
Para que los estudiantes comiencen a consultar inmediatamente el nuevo reglamento:
1. En la fila del reglamento aprobado, presione el botón **«Activar»**.
2. El sistema conmutará la versión activa en menos de 20 milisegundos.
3. A partir de ese instante, el 100% de las consultas del chat público se resolverán utilizando exclusivamente los chunks y artículos de esta nueva versión.

### 4.6. Cierre de Sesión Seguro
Para salir de la interfaz administrativa, presione el botón **«Cerrar Sesión»** en la esquina superior derecha. Esto destruirá la cookie de sesión y bloqueará inmediatamente el acceso a las rutas protegidas.

---
*Fin del Documento 08 — Manual de Usuario del Sistema.*
