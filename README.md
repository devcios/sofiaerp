# Sofia ERP 2024

Sofia ERP es un software open source apps basada en licencia LGPL.

Para mayor información [http://sofiaerp.com](http://sofiaerp.com)

---

## 🚀 Guía de Instalación (Docker Odoo 15)

Este proyecto está configurado para ejecutarse en contenedores Docker, optimizado con PostgreSQL 13 y multiprocesamiento (Workers).

### 1. Configuración Inicial (Variables de Entorno)
Antes de levantar el proyecto por primera vez, asegúrate de tener configurado tu archivo `.env`. Si no lo tienes, copia la plantilla:
```bash
cp .env.example .env
```
*Edita el archivo `.env` para establecer tus contraseñas y configuraciones deseadas.*

### 2. Levantar el Proyecto

Dependiendo de tu situación, utiliza uno de los siguientes comandos:

**Opción A: Instalación desde Cero (Nueva)**
Si es la primera vez que instalas el proyecto, o deseas borrar todos los datos antiguos para empezar de cero, ejecuta:
```bash
# Borra contenedores viejos y limpia los volúmenes huérfanos
docker-compose down -v 

# Construye la imagen y levanta los servicios en segundo plano
docker-compose up -d --build
```

**Opción B: Reiniciar manteniendo los datos**
Si ya tienes datos guardados y solo deseas reiniciar los servicios aplicando cambios de código o de configuración:
```bash
docker-compose down
docker-compose up -d --build
```

### 3. Verificar los Logs
Para asegurarte de que Odoo ha arrancado correctamente, puedes ver los registros en tiempo real:
```bash
docker logs -f odoo15
```
*(Presiona `Ctrl+C` para salir de los logs).*

### 4. Acceder al Sistema
Una vez que el sistema esté corriendo, ingresa a tu navegador web y ve a:
```
http://localhost:8069/web/database/selector
```
