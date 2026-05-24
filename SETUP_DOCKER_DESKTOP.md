# Docker Desktop Setup — Opción A (Build en Windows)

**Objetivo:** Dockerizar SDAI en Windows, subir imagen a GitHub Container Registry, desplegar desde cualquier Linux device.

---

## 1. Instala Docker Desktop

- **URL:** https://www.docker.com/products/docker-desktop
- **Descarga:** Windows installer
- **Instala** y **reinicia Windows**
- Esto instala Docker daemon + docker compose CLI

---

## 2. Verifica instalación (PowerShell)

```powershell
docker --version
docker compose version
```

Ambos deben mostrar versión. Espera ~30s a que Docker daemon inicie (icono en system tray).

---

## 3. Build imagen en Windows

Desde `C:\Users\silva\Desktop\proyecto_franklin\`:

```powershell
cd C:\Users\silva\Desktop\proyecto_franklin
docker compose build
```

Output debe terminar con:
```
[+] Building 45.2s (11/11) FINISHED
=> => naming to sdai/sensor:0.1.0
```

Toma ~1-2 min primera vez (pip install).

---

## 4. Configura GitHub Container Registry (GHCR)

### 4a. Crea Personal Access Token en GitHub

1. Abre https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: `DOCKER_PUSH_TOKEN`
4. Scopes: selecciona `write:packages` + `delete:packages`
5. Expiry: 90 days (o más)
6. Click "Generate token"
7. **Copia el token** (no podrás verlo después)

### 4b. Login a GHCR desde Windows

```powershell
$env:GITHUB_TOKEN = "ghp_xxxxx..."  # Pega tu token aquí
echo $env:GITHUB_TOKEN | docker login ghcr.io -u silvaisaac148 --password-stdin
```

Output: `Login Succeeded`

---

## 5. Tag e push imagen a GHCR

```powershell
docker tag sdai/sensor:0.1.0 ghcr.io/silvaisaac148/sdai/sensor:0.1.0
docker push ghcr.io/silvaisaac148/sdai/sensor:0.1.0
```

Output final:
```
0.1.0: digest: sha256:abc123... size: 2048
```

---

## 6. Actualiza docker-compose.yml para usar GHCR

En `C:\Users\silva\Desktop\proyecto_franklin\docker-compose.yml`, cambia:

```yaml
services:
  sdai-sensor:
    image: ghcr.io/silvaisaac148/sdai/sensor:0.1.0  # ← cambio aquí
    # Quita la sección build:
    # build:
    #   context: .
    #   dockerfile: Dockerfile
```

Git commit:
```powershell
git add docker-compose.yml
git commit -m "chore: use GHCR image instead of local build"
git push
```

---

## 7. Despliega en Linux (cualquier device)

En máquina Linux (VM, cloud, raspberry, etc.):

```bash
git clone https://github.com/silvaisaac148/SDAI.git
cd SDAI
cp /path/to/.env .env  # Copia .env de dónde sea (Windows, shared folder, etc.)
docker compose up -d
```

Docker automáticamente:
- Hace pull de `ghcr.io/silvaisaac148/sdai/sensor:0.1.0`
- Arranca contenedor con .env inyectado
- Healthcheck cada 30s

---

## 8. Valida en Linux

```bash
docker compose ps
curl http://localhost:8000/health
docker compose exec sdai-sensor python scripts/simulate_attacks.py
```

---

## Resumen

| Step | Máquina | Acción |
|------|---------|--------|
| 1-3 | Windows | Instala Docker, build imagen local |
| 4-5 | Windows | Push a GHCR |
| 6 | Windows | Actualiza docker-compose.yml, git push |
| 7-8 | **Cualquier Linux** | Clone repo, .env, docker compose up |

**Ventaja:** Imagen construida UNA VEZ. Desplegable INFINITAS veces sin rebuild.

---

## Troubleshooting

**Error: `docker: command not found`**
- Docker Desktop no inició. Abre la app desde Start Menu y espera ~30s.

**Error: `denied: permission denied while trying to connect to the Docker daemon`**
- En Windows: reinicia PowerShell como Admin.

**Error: `denied: resource not found` en docker push**
- Token expiró o sin scope `write:packages`. Crea uno nuevo.

**Imagen no baja en Linux**
- GHCR es privado por defecto. Ve a https://github.com/silvaisaac148/SDAI/packages y cambia a "Public".

---

**Next step después de restart:** Vuelve a Claude Code y di "Docker Desktop instalado", empezamos con paso 2.
