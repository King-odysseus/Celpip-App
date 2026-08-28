import { useNavigate } from 'react-router-dom'
import { Button, Card, CardTitle } from '../../components/ui'
import { useAuth } from './AuthProvider'
import { ProfileForm } from './ProfileForm'

export function AccountPage() {
  const { user, profile, logout } = useAuth()
  const navigate = useNavigate()

  async function onSignOut() {
    await logout()
    navigate('/', { replace: true })
  }

  return (
    <section aria-labelledby="account-title" className="space-y-5">
      <header className="space-y-1.5">
        <p className="eyebrow">Your account</p>
        <h1
          id="account-title"
          className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl"
        >
          Account &amp; profile
        </h1>
        <p className="max-w-2xl text-sm text-muted sm:text-base">
          Set your exam date, targets, and study availability. These power your
          dashboard countdown and, later, your study plan.
        </p>
      </header>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>Signed in</CardTitle>
            <p className="mt-1 text-sm text-muted">
              {user?.identifier}
              {user?.email ? ` · ${user.email}` : ''}
            </p>
          </div>
          <Button type="button" variant="secondary" onClick={onSignOut}>
            Sign out
          </Button>
        </div>
      </Card>

      <Card>
        <CardTitle className="mb-4">Study profile</CardTitle>
        {profile ? (
          <ProfileForm profile={profile} />
        ) : (
          <p role="status" className="text-sm text-muted">
            Loading your profile…
          </p>
        )}
      </Card>
    </section>
  )
}
