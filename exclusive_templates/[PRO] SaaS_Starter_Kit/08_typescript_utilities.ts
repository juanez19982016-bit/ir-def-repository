// ============================================================
// 🔧 TYPESCRIPT UTILITY COLLECTION — 30+ Production Utilities
// DevVault Pro 2026 — Copy-paste into any TypeScript project
// ============================================================

// ── 1. Type-safe Object Utilities ────────────────

/** Pick only defined (non-undefined) keys */
export type DefinedKeys<T> = {
    [K in keyof T]-?: undefined extends T[K] ? never : K
}[keyof T]

/** Make specific keys optional */
export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>

/** Make specific keys required */
export type RequiredBy<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>

/** Deep partial — makes all nested properties optional */
export type DeepPartial<T> = {
    [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K]
}

/** Type-safe Object.keys() */
export const typedKeys = <T extends object>(obj: T) =>
    Object.keys(obj) as Array<keyof T>

/** Type-safe Object.entries() */
export const typedEntries = <T extends object>(obj: T) =>
    Object.entries(obj) as Array<[keyof T, T[keyof T]]>

/** Omit properties by value type */
export type OmitByValue<T, V> = {
    [K in keyof T as T[K] extends V ? never : K]: T[K]
}


// ── 2. String Utilities ──────────────────────────

/** Capitalize first letter */
export const capitalize = (s: string) =>
    s.charAt(0).toUpperCase() + s.slice(1)

/** Convert to slug */
export const slugify = (s: string) =>
    s.toLowerCase().trim()
        .replace(/[^\w\s-]/g, '')
        .replace(/[\s_-]+/g, '-')
        .replace(/^-+|-+$/g, '')

/** Truncate with ellipsis */
export const truncate = (s: string, len: number) =>
    s.length <= len ? s : `${s.slice(0, len)}...`

/** Generate random string */
export const randomId = (len = 12) =>
    crypto.randomUUID().replace(/-/g, '').slice(0, len)

/** Format number with commas */
export const formatNumber = (n: number) =>
    new Intl.NumberFormat('en-US').format(n)

/** Format currency */
export const formatCurrency = (amount: number, currency = 'USD') =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount)

/** Format relative time ("2 hours ago") */
export const timeAgo = (date: Date): string => {
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
    const intervals = [
        { label: 'year', seconds: 31536000 },
        { label: 'month', seconds: 2592000 },
        { label: 'week', seconds: 604800 },
        { label: 'day', seconds: 86400 },
        { label: 'hour', seconds: 3600 },
        { label: 'minute', seconds: 60 },
    ]
    for (const { label, seconds: s } of intervals) {
        const count = Math.floor(seconds / s)
        if (count >= 1) return `${count} ${label}${count > 1 ? 's' : ''} ago`
    }
    return 'just now'
}


// ── 3. Array Utilities ───────────────────────────

/** Group array by key */
export const groupBy = <T>(arr: T[], key: keyof T): Record<string, T[]> =>
    arr.reduce((acc, item) => {
        const group = String(item[key])
            ; (acc[group] ??= []).push(item)
        return acc
    }, {} as Record<string, T[]>)

/** Unique by key */
export const uniqueBy = <T>(arr: T[], key: keyof T): T[] =>
    [...new Map(arr.map(item => [item[key], item])).values()]

/** Chunk array into smaller arrays */
export const chunk = <T>(arr: T[], size: number): T[][] =>
    Array.from({ length: Math.ceil(arr.length / size) }, (_, i) =>
        arr.slice(i * size, i * size + size)
    )

/** Shuffle array (Fisher-Yates) */
export const shuffle = <T>(arr: T[]): T[] => {
    const a = [...arr]
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
            ;[a[i], a[j]] = [a[j], a[i]]
    }
    return a
}

/** Sort by multiple keys */
export const sortBy = <T>(arr: T[], ...keys: (keyof T)[]) =>
    [...arr].sort((a, b) => {
        for (const key of keys) {
            if (a[key] < b[key]) return -1
            if (a[key] > b[key]) return 1
        }
        return 0
    })

/** Flatten nested array (type-safe) */
export const flatten = <T>(arr: (T | T[])[]): T[] =>
    arr.flat() as T[]


// ── 4. Async Utilities ───────────────────────────

/** Sleep / delay */
export const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

/** Retry with exponential backoff */
export const retry = async <T>(
    fn: () => Promise<T>,
    maxRetries = 3,
    baseDelay = 1000
): Promise<T> => {
    for (let i = 0; i <= maxRetries; i++) {
        try {
            return await fn()
        } catch (error) {
            if (i === maxRetries) throw error
            await sleep(baseDelay * Math.pow(2, i))
        }
    }
    throw new Error('Unreachable')
}

/** Debounce function */
export const debounce = <T extends (...args: any[]) => any>(fn: T, ms: number) => {
    let timer: ReturnType<typeof setTimeout>
    return (...args: Parameters<T>) => {
        clearTimeout(timer)
        timer = setTimeout(() => fn(...args), ms)
    }
}

/** Throttle function */
export const throttle = <T extends (...args: any[]) => any>(fn: T, ms: number) => {
    let lastCall = 0
    return (...args: Parameters<T>) => {
        const now = Date.now()
        if (now - lastCall >= ms) {
            lastCall = now
            return fn(...args)
        }
    }
}

/** Promise.allSettled with typed results */
export const allSettledTyped = async <T extends readonly Promise<any>[]>(
    promises: T
) => {
    const results = await Promise.allSettled(promises)
    return {
        fulfilled: results.filter((r): r is PromiseFulfilledResult<any> => r.status === 'fulfilled').map(r => r.value),
        rejected: results.filter((r): r is PromiseRejectedResult => r.status === 'rejected').map(r => r.reason),
    }
}


// ── 5. Object Utilities ──────────────────────────

/** Deep clone (structuredClone wrapper) */
export const deepClone = <T>(obj: T): T => structuredClone(obj)

/** Deep merge objects */
export const deepMerge = <T extends object>(target: T, ...sources: Partial<T>[]): T => {
    const result = { ...target }
    for (const source of sources) {
        for (const key of Object.keys(source) as (keyof T)[]) {
            const val = source[key]
            if (val && typeof val === 'object' && !Array.isArray(val)) {
                (result as any)[key] = deepMerge((result as any)[key] ?? {}, val as any)
            } else if (val !== undefined) {
                (result as any)[key] = val
            }
        }
    }
    return result
}

/** Pick keys from object */
export const pick = <T extends object, K extends keyof T>(obj: T, keys: K[]): Pick<T, K> =>
    keys.reduce((acc, key) => {
        if (key in obj) acc[key] = obj[key]
        return acc
    }, {} as Pick<T, K>)

/** Omit keys from object */
export const omit = <T extends object, K extends keyof T>(obj: T, keys: K[]): Omit<T, K> => {
    const result = { ...obj }
    keys.forEach(key => delete result[key])
    return result
}


// ── 6. Validation Utilities ──────────────────────

export const isEmail = (s: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)
export const isURL = (s: string) => { try { new URL(s); return true } catch { return false } }
export const isUUID = (s: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-7][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s)
export const isEmpty = (v: any): boolean => v == null || v === '' || (Array.isArray(v) && v.length === 0) || (typeof v === 'object' && Object.keys(v).length === 0)


// ── 7. Color Utilities ──────────────────────────

/** Hex to RGB */
export const hexToRgb = (hex: string) => {
    const n = parseInt(hex.replace('#', ''), 16)
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 }
}

/** RGB to Hex */
export const rgbToHex = (r: number, g: number, b: number) =>
    '#' + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('')

/** Generate HSL color palette */
export const generatePalette = (hue: number, count = 10) =>
    Array.from({ length: count }, (_, i) => {
        const lightness = 95 - (i * 8)
        return `hsl(${hue}, 70%, ${lightness}%)`
    })


// ── 8. Error Handling ────────────────────────────

/** Type-safe Result pattern (no try-catch needed) */
export type Result<T, E = Error> = { ok: true; value: T } | { ok: false; error: E }

export const ok = <T>(value: T): Result<T, never> => ({ ok: true, value })
export const err = <E>(error: E): Result<never, E> => ({ ok: false, error })

/** Wrap async function in Result */
export const tryCatch = async <T>(fn: () => Promise<T>): Promise<Result<T>> => {
    try { return ok(await fn()) }
    catch (e) { return err(e instanceof Error ? e : new Error(String(e))) }
}


// ── 9. Environment & Config ──────────────────────

/** Type-safe env variable getter */
export const env = <T extends string>(key: string, fallback?: T): T => {
    const value = process.env[key] as T | undefined
    if (value === undefined) {
        if (fallback !== undefined) return fallback
        throw new Error(`Missing env var: ${key}`)
    }
    return value
}

/** Assert condition (throws if false) */
export function assert(condition: any, message = 'Assertion failed'): asserts condition {
    if (!condition) throw new Error(message)
}

/** Exhaustive check (TypeScript never type) */
export const exhaustive = (value: never): never => {
    throw new Error(`Unhandled value: ${value}`)
}
