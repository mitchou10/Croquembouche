import { type Http, ok } from './http.js'
import type { PurgeOut } from './types.js'

/** What a person sent to be analysed, and forgetting it. */
export class Users {
  constructor(private readonly http: Http) {}

  /** Deletes what the token sent to be analysed: its uses of analyses, its searches and the documents it sent. Not the
   *  models, nor their example documents, nor the analyses. For a service account, that is all that it sent. */
  purgeMyData(): Promise<PurgeOut> {
    return ok(this.http.DELETE('/api/users/me/data'))
  }

  /** The same for another person (the identifier of their account): administrators only (`ForbiddenError`). */
  purge(userId: string): Promise<PurgeOut> {
    return ok(this.http.DELETE('/api/users/{user_id}/data', { params: { path: { user_id: userId } } }))
  }
}
