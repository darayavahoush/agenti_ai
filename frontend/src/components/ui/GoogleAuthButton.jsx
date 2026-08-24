import { GoogleLogin } from '@react-oauth/google'

/** Thin wrapper around @react-oauth/google's GoogleLogin widget. Our
 * backend's google_oauth.py verifies an ID token (a JWT it can check
 * the signature/audience/expiry of offline, no client secret needed),
 * not an opaque OAuth access token -- GoogleLogin's onSuccess callback
 * is the one that hands back a `credential` field containing exactly
 * that ID token, which is what gets forwarded to the backend as-is.
 *
 * Disabled while `disabled` is true (e.g. required fields not filled
 * in yet on the register form).
 */
export default function GoogleAuthButton({ onIdToken, onError, disabled, text = 'continue_with' }) {
  return (
    <div className={disabled ? 'opacity-50 pointer-events-none' : ''}>
      <GoogleLogin
        onSuccess={(credentialResponse) => {
          if (!credentialResponse.credential) {
            onError?.('No credential returned from Google')
            return
          }
          onIdToken(credentialResponse.credential)
        }}
        onError={() => onError?.('Google sign-in was cancelled or failed')}
        text={text}
        shape="pill"
        width="100%"
      />
    </div>
  )
}
