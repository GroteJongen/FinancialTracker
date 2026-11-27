// Static Compose checks; never starts a daemon or touches a user database.
import assert from 'node:assert/strict'
import { execFileSync, spawnSync } from 'node:child_process'
const version = 'sha-' + '1'.repeat(40)
const env = { ...process.env, POSTGRES_PASSWORD: 'synthetic-validation-only', APP_VERSION: version, IMAGE_PREFIX: 'ghcr.io/grotejongen/financialtracker' }
const args = ['compose', '--env-file', '.env.example', '-f', 'compose.ghcr.yaml', 'config', '--format', 'json']
const config = JSON.parse(execFileSync('docker', args, { env, encoding: 'utf8' }))
assert.equal(config.name, process.env.COMPOSE_PROJECT_NAME ?? 'financialtracker')
for (const service of Object.values(config.services)) assert.equal(service.build, undefined)
assert.equal(config.services.backend.image, `ghcr.io/grotejongen/financialtracker-backend:${version}`)
assert.equal(config.services.migrate.image, config.services.backend.image)
assert.equal(config.services.frontend.image, `ghcr.io/grotejongen/financialtracker-frontend:${version}`)
assert.equal(config.services.db.ports, undefined)
assert.equal(config.services.db.volumes[0].source, 'postgres-data')
assert.equal(config.volumes['postgres-data'].name, config.name + '_postgres-data')
for (const service of ['backend', 'frontend']) assert.equal(config.services[service].ports[0].host_ip, '127.0.0.1')
assert.equal(config.services.backend.depends_on.migrate.condition, 'service_completed_successfully')
const missing = spawnSync('docker', args, { env: { ...env, APP_VERSION: '' }, encoding: 'utf8' })
assert.notEqual(missing.status, 0)
assert.match(missing.stderr, /APP_VERSION/)
console.log('PASS: GHCR Compose requires one release, preserves volume, has no builds and binds only localhost')
