import { Outlet, Link } from 'react-router-dom'
import { Container, Navbar, Nav, NavDropdown, Dropdown } from 'react-bootstrap'
import { useAuth } from '../contexts/AuthContext'
import { t, changeLanguage, getCurrentLanguage } from '../lib/i18n'
import { useState, useEffect } from 'react'
import NotificationBell from './NotificationBell'

export default function AppLayout() {
  const { user, logout } = useAuth()
  const [language, setLanguage] = useState(getCurrentLanguage())
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const stored = window.localStorage.getItem('actionhub_theme')
    if (stored === 'dark' || stored === 'light') return stored
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark'
    return 'light'
  })

  useEffect(() => {
    setLanguage(getCurrentLanguage())
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    window.localStorage.setItem('actionhub_theme', theme)
  }, [theme])

  const handleLogout = () => {
    logout()
  }

  const handleLanguageChange = (lng: string) => {
    changeLanguage(lng)
    setLanguage(lng)
  }

  const toggleTheme = () => {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'))
  }

  const isAdmin = user?.role === 'Admin'
  const leadsTeams = user?.leads_teams || []
  const isTeamLead = leadsTeams.length > 0

  return (
    <div className="d-flex flex-column min-vh-100">
      <Navbar expand="lg" className="navbar">
        <Container fluid>
          <Navbar.Brand as={Link} to="/" style={{ fontWeight: 700 }}>
            {t('app.title', 'ActionHub')}
          </Navbar.Brand>
          
          <Navbar.Toggle aria-controls="main-nav" />
          
          <Navbar.Collapse id="main-nav">
            <Nav className="me-auto">

              <Nav.Link as={Link} to="/meetings/series">
                {t('meetings.series', 'Meeting Series')}
              </Nav.Link>

              <Nav.Link as={Link} to="/actions">
                {t('nav.actions', 'Actions')}
              </Nav.Link>

              <Nav.Link as={Link} to="/decisions">
                {t('nav.decisions', 'Decisions')}
              </Nav.Link>

              <NavDropdown title={t('nav.dashboard', 'Dashboard')} id="dashboard-dropdown">
                <NavDropdown.Item as={Link} to="/dashboard/personal">
                  {t('nav.personalDashboard', 'Personal Dashboard')}
                </NavDropdown.Item>
                <NavDropdown.Item as={Link} to="/dashboard/global">
                  {t('nav.globalDashboard', 'Global Dashboard')}
                </NavDropdown.Item>
                {isTeamLead && (
                  <NavDropdown.Item as={Link} to="/dashboard/team">
                    {t('nav.teamDashboard', 'My Team Dashboard')}
                  </NavDropdown.Item>
                )}
              </NavDropdown>

              {isAdmin && (
                <NavDropdown title={t('nav.admin', 'Admin')} id="admin-dropdown">
                  <NavDropdown.Item as={Link} to="/admin/users">
                    {t('nav.users', 'Users')}
                  </NavDropdown.Item>
                  <NavDropdown.Item as={Link} to="/admin/teams">
                    {t('nav.teams', 'Teams')}
                  </NavDropdown.Item>
                  <NavDropdown.Item as={Link} to="/admin/categories">
                    {t('nav.businessThemes', 'Categories')}
                  </NavDropdown.Item>
                </NavDropdown>
              )}

              <Nav.Link as={Link} to="/instructions">
                {t('nav.instructions', 'Instructions')}
              </Nav.Link>
            </Nav>

            <Nav className="align-items-center gap-2">
              {/* Notification Bell */}
              <NotificationBell />

              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={toggleTheme}
                title={theme === 'dark' ? t('common.lightMode', 'Switch to light mode') : t('common.darkMode', 'Switch to dark mode')}
              >
                {theme === 'dark' ? t('common.lightMode', 'Light') : t('common.darkMode', 'Dark')}
              </button>

              {/* Language Dropdown */}
              <Dropdown align="end">
                <Dropdown.Toggle
                  variant="outline-secondary"
                  id="language-dropdown"
                  style={{
                    borderColor: 'var(--brand-border)',
                    color: 'var(--brand-dark)',
                    backgroundColor: 'transparent',
                  }}
                >
                  {language === 'zh' ? '中文' : 'EN'}
                </Dropdown.Toggle>
                
                <Dropdown.Menu>
                  <Dropdown.Item onClick={() => handleLanguageChange('en')}>
                    English
                  </Dropdown.Item>
                  <Dropdown.Item onClick={() => handleLanguageChange('zh')}>
                    中文
                  </Dropdown.Item>
                </Dropdown.Menu>
              </Dropdown>

              {/* User Dropdown */}
              <NavDropdown title={user?.display_name || user?.username} id="user-dropdown">
                <NavDropdown.Item disabled>
                  {user?.role}
                </NavDropdown.Item>
                <NavDropdown.Divider />
                <NavDropdown.Item onClick={handleLogout}>
                  {t('auth.logout', 'Logout')}
                </NavDropdown.Item>
              </NavDropdown>
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      <Container fluid className="flex-grow-1 py-3">
        <Outlet />
      </Container>

      <footer className="py-2 text-center" style={{ backgroundColor: 'var(--brand-light)', color: 'var(--brand-muted)' }}>
        <small>ActionHub v3.41</small>
      </footer>
    </div>
  )
}