import { describe, expect, it } from 'vitest'

import { dictionaryKeys } from './t'

describe('i18n parity (NFR-07)', () => {
  it('has the same keys in en and ta', () => {
    expect([...dictionaryKeys.ta].sort()).toEqual([...dictionaryKeys.en].sort())
  })
})
