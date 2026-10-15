import { describe, it, expect } from 'vitest'
import { cn, formatFileSize, formatDuration, formatConfidence, validateFile } from '@/lib/utils'

describe('Utility Functions', () => {
  describe('cn', () => {
    it('joins class names', () => {
      expect(cn('a', 'b', 'c')).toBe('a b c')
    })

    it('filters falsy values', () => {
      expect(cn('a', false, 'b', null, 'c')).toBe('a b c')
    })
  })

  describe('formatFileSize', () => {
    it('formats bytes', () => {
      expect(formatFileSize(0)).toBe('0 Bytes')
      expect(formatFileSize(1024)).toBe('1 KB')
      expect(formatFileSize(1024 * 1024)).toBe('1 MB')
      expect(formatFileSize(1024 * 1024 * 1024)).toBe('1 GB')
    })
  })

  describe('formatDuration', () => {
    it('formats milliseconds', () => {
      expect(formatDuration(500)).toBe('500ms')
      expect(formatDuration(1500)).toBe('1.5s')
      expect(formatDuration(60000)).toBe('1.0m')
    })
  })

  describe('formatConfidence', () => {
    it('formats confidence as percentage', () => {
      expect(formatConfidence(0.5)).toBe('50.0%')
      expect(formatConfidence(0.876)).toBe('87.6%')
      expect(formatConfidence(1)).toBe('100.0%')
    })
  })

  describe('validateFile', () => {
    const allowedTypes = ['image/jpeg', 'image/png']
    const maxSize = 1024 * 1024 // 1MB

    it('returns null for valid file', () => {
      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
      Object.defineProperty(file, 'size', { value: 100 })
      expect(validateFile(file, allowedTypes, maxSize)).toBeNull()
    })

    it('rejects invalid type', () => {
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
      Object.defineProperty(file, 'size', { value: 100 })
      expect(validateFile(file, allowedTypes, maxSize)).toContain('not allowed')
    })

    it('rejects oversized file', () => {
      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
      Object.defineProperty(file, 'size', { value: maxSize + 1 })
      expect(validateFile(file, allowedTypes, maxSize)).toContain('exceeds maximum')
    })
  })
})