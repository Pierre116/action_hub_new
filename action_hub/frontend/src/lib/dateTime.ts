export type DateTimeInput = string | number | Date | null | undefined

const CHINA_TIME_ZONE = 'Asia/Shanghai'

const DATE_ONLY_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/
const NAIVE_TIMESTAMP_PATTERN = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?$/

function getChinaDateParts(value: DateTimeInput = new Date()): { year: number; month: number; day: number } | null {
  const parsed = toValidDate(value)
  if (!parsed) return null
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: CHINA_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  const parts = formatter.formatToParts(parsed)
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  const year = Number.parseInt(values.year || '', 10)
  const month = Number.parseInt(values.month || '', 10)
  const day = Number.parseInt(values.day || '', 10)
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) {
    return null
  }
  return { year, month, day }
}

function toValidDate(value: DateTimeInput): Date | null {
  if (value == null || value === '') return null
  if (value instanceof Date) {
    const parsedDate = new Date(value.getTime())
    return Number.isNaN(parsedDate.getTime()) ? null : parsedDate
  }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    const dateOnly = trimmed.match(DATE_ONLY_PATTERN)
    if (dateOnly) {
      const [, year, month, day] = dateOnly
      const parsedDate = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day), 0, 0, 0, 0))
      return Number.isNaN(parsedDate.getTime()) ? null : parsedDate
    }

    const hasExplicitTimeZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(trimmed)
    const naiveTimestamp = trimmed.match(NAIVE_TIMESTAMP_PATTERN)
    if (naiveTimestamp && !hasExplicitTimeZone) {
      const [, year, month, day, hour, minute, second = '0', fractional = '0'] = naiveTimestamp
      const milliseconds = Number(fractional.padEnd(3, '0').slice(0, 3))
      const parsedDate = new Date(
        Date.UTC(
          Number(year),
          Number(month) - 1,
          Number(day),
          Number(hour),
          Number(minute),
          Number(second),
          milliseconds,
        ),
      )
      return Number.isNaN(parsedDate.getTime()) ? null : parsedDate
    }
  }

  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function getFormatter(includeTime: boolean, includeSeconds: boolean): Intl.DateTimeFormat {
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: CHINA_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...(includeTime
      ? {
          hour: '2-digit',
          minute: '2-digit',
          ...(includeSeconds ? { second: '2-digit' } : {}),
          hour12: false,
        }
      : {}),
  })
}

function buildFormattedValue(value: DateTimeInput, includeTime: boolean, includeSeconds: boolean): string {
  if (value == null || value === '') return '-'
  const parsed = toValidDate(value)
  if (!parsed) return String(value)
  const formatter = getFormatter(includeTime, includeSeconds)
  const parts = formatter.formatToParts(parsed)
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  const date = `${values.year}-${values.month}-${values.day}`
  if (!includeTime) return date
  const time = includeSeconds
    ? `${values.hour}:${values.minute}:${values.second}`
    : `${values.hour}:${values.minute}`
  return `${date} ${time}`
}

export function formatChinaDate(value: DateTimeInput): string {
  return buildFormattedValue(value, false, false)
}

export function formatChinaDateTime(value: DateTimeInput): string {
  return buildFormattedValue(value, true, true)
}

export function formatChinaDateTimeNoSeconds(value: DateTimeInput): string {
  return buildFormattedValue(value, true, false)
}

export function currentChinaDateISO(value: DateTimeInput = new Date()): string {
  const parts = getChinaDateParts(value)
  if (!parts) return '-'
  return `${parts.year}-${String(parts.month).padStart(2, '0')}-${String(parts.day).padStart(2, '0')}`
}

export function addChinaDaysISO(days: number, value: DateTimeInput = new Date()): string {
  const parts = getChinaDateParts(value)
  if (!parts) return '-'
  const base = new Date(Date.UTC(parts.year, parts.month - 1, parts.day))
  base.setUTCDate(base.getUTCDate() + days)
  return currentChinaDateISO(base)
}
