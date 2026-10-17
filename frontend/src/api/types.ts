// Aliases over the generated OpenAPI types (never hand-written API types: CLAUDE.md §4).
import type { components } from './schema'

type S = components['schemas']

export type AlertItem = S['AlertItem']
export type AssessmentResult = S['AssessmentResult']
export type ClockOut = S['ClockOut']
export type ConsoleMessage = S['ConsoleMessageOut']
export type ContactRequest = S['ContactRequestOut']
export type CustomerOverview = S['CustomerOverview']
export type CustomerRisk = S['CustomerRisk']
export type CustomerTransferIn = S['CustomerTransferIn']
export type CustomerTransferOut = S['CustomerTransferOut']
export type EpisodeOut = S['EpisodeOut']
export type HoldDetail = S['HoldDetail']
export type HoldListItem = S['HoldListItem']
export type LoginResponse = S['LoginResponse']
export type OfficerDecisionIn = S['OfficerDecisionIn']
export type Reason = S['ReasonOut']
export type ReportOut = S['ReportOut']
export type ReportPatchIn = S['ReportPatchIn']
export type RunOut = S['RunOut']
export type ScenarioOut = S['ScenarioOut']
export type ScriptOut = S['ScriptOut']
export type Summary = S['Summary']
export type TimelineItem = S['TimelineItem']
export type TransferStatusOut = S['TransferStatusOut']
export type TrustedResponseOut = S['TrustedResponseOut']
export type TrustedView = S['TrustedView']
export type User = S['UserOut']
export type WatchPoint = S['WatchPointOut']
export type Page<T> = { items: T[]; next_cursor: string | null }

export type Tier = Reason extends never ? never : AssessmentResult['tier']
export type Role = User['role']
export type HoldStatus = HoldDetail['status']
export type ContactResponse = NonNullable<HoldDetail['contact_response']>
export type Lang = 'en' | 'ta'
