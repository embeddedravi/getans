import { Link } from "react-router-dom";
import { ThemeToggle } from "../components/ThemeToggle";

const Arrow = () => <svg aria-hidden="true" viewBox="0 0 20 20" fill="none" className="h-4 w-4"><path d="M4 10h12m-5-5 5 5-5 5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>;

export function PublicIndexPage() {
  const signedIn = Boolean(localStorage.getItem("access_token"));
  return <div className="min-h-screen overflow-hidden bg-base-100 text-base-content">
    <header className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-10">
      <Link to="/" className="flex items-center gap-3" aria-label="GetANS home">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-content shadow-lg shadow-primary/20"><svg viewBox="0 0 24 24" fill="none" className="h-6 w-6"><path d="M4 18V6l8 8 8-8v12" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
        <span><span className="block font-display text-lg font-bold leading-none tracking-tight">GetANS</span><span className="mt-1 block text-[10px] font-semibold uppercase tracking-[.2em] text-base-content/45">Ad network platform</span></span>
      </Link>
      <nav className="hidden items-center gap-8 text-sm font-medium text-base-content/65 md:flex" aria-label="Main navigation">
        <a className="transition hover:text-base-content" href="#platform">Platform</a><a className="transition hover:text-base-content" href="#how-it-works">How it works</a><a className="transition hover:text-base-content" href="#for-you">For you</a>
      </nav>
      <div className="flex items-center gap-2 sm:gap-3">
        <ThemeToggle placement="inline" />
        <Link to={signedIn ? "/home" : "/login"} className="btn btn-ghost btn-sm hidden sm:inline-flex">{signedIn ? "Dashboard" : "Sign in"}</Link>
        <Link to="/signup" className="btn btn-primary btn-sm sm:btn-md">Get started <Arrow /></Link>
      </div>
    </header>

    <main>
      <section className="relative mx-auto grid max-w-7xl items-center gap-12 px-5 pb-20 pt-10 sm:px-8 sm:pb-28 sm:pt-16 lg:grid-cols-[1.05fr_.95fr] lg:px-10 lg:pt-20">
        <div className="pointer-events-none absolute -left-48 top-16 h-[28rem] w-[28rem] rounded-full bg-primary/10 blur-[100px]" />
        <div className="relative z-[1] landing-rise">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1.5 text-xs font-semibold text-primary"><span className="h-1.5 w-1.5 rounded-full bg-primary" /> One network. Two ways to grow.</div>
          <h1 className="mt-7 max-w-2xl font-display text-5xl font-semibold leading-[1.04] tracking-[-.045em] sm:text-6xl lg:text-7xl">Make your next impression <span className="text-primary">count.</span></h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-base-content/65 sm:text-lg sm:leading-8">A clearer way for advertisers to reach people and publishers to earn from their audience. Campaigns, inventory, and performance come together in one workspace.</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link to="/signup" className="btn btn-primary btn-lg shadow-lg shadow-primary/15">Start with GetANS <Arrow /></Link>
            <Link to="/login" className="btn btn-outline btn-lg">Explore your dashboard</Link>
          </div>
          <div className="mt-9 flex flex-wrap gap-x-6 gap-y-3 text-xs font-medium text-base-content/55">
            <span className="flex items-center gap-2"><span className="text-success">✓</span> Built for both sides of the network</span><span className="flex items-center gap-2"><span className="text-success">✓</span> Performance in one place</span>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-xl lg:ml-auto">
          <div className="absolute -inset-8 rounded-[2.5rem] bg-gradient-to-br from-primary/20 via-secondary/10 to-transparent blur-2xl" />
          <div className="relative landing-drift rounded-2xl border border-base-content/10 bg-base-200 p-3 shadow-2xl shadow-base-content/10 sm:p-4">
            <div className="overflow-hidden rounded-xl border border-base-300 bg-base-100">
              <div className="flex items-center justify-between border-b border-base-300 px-5 py-4"><div className="flex items-center gap-3"><div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary"><svg viewBox="0 0 24 24" className="h-4 w-4" fill="none"><path d="M4 18V6l8 8 8-8v12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg></div><div><p className="text-xs font-semibold">Dashboard preview</p><p className="text-[10px] text-base-content/50">Example workspace</p></div></div><span className="badge badge-primary badge-sm">Preview</span></div>
              <div className="grid grid-cols-2 gap-3 p-4 sm:gap-4 sm:p-5"><div className="rounded-xl bg-base-200 p-4"><p className="text-[11px] text-base-content/55">Impressions</p><p className="mt-2 font-display text-2xl font-semibold">248.6k</p><p className="mt-1 text-[10px] text-success">↗ Delivery across your network</p></div><div className="rounded-xl bg-base-200 p-4"><p className="text-[11px] text-base-content/55">Engagement</p><p className="mt-2 font-display text-2xl font-semibold">3.84%</p><p className="mt-1 text-[10px] text-primary">Clicks & conversions</p></div></div>
              <div className="px-4 pb-5 sm:px-5"><div className="mb-3 flex items-center justify-between"><p className="text-xs font-semibold">Performance trend</p><span className="text-[10px] text-base-content/45">This week</span></div><div className="relative h-36 overflow-hidden rounded-lg bg-base-200/60 p-3">
                <div className="absolute inset-x-3 top-1/4 border-t border-dashed border-base-300"/><div className="absolute inset-x-3 top-2/4 border-t border-dashed border-base-300"/><div className="absolute inset-x-3 top-3/4 border-t border-dashed border-base-300"/>
                <svg viewBox="0 0 560 125" preserveAspectRatio="none" className="relative h-full w-full"><defs><linearGradient id="trend-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="currentColor" stopOpacity=".24"/><stop offset="1" stopColor="currentColor" stopOpacity="0"/></linearGradient></defs><path d="M0 101 C35 100 42 72 84 78 S132 86 168 61 S222 77 252 54 S306 62 338 34 S387 49 421 30 S475 42 503 17 S541 23 560 6 L560 125 L0 125Z" fill="url(#trend-fill)" className="text-primary"/><path d="M0 101 C35 100 42 72 84 78 S132 86 168 61 S222 77 252 54 S306 62 338 34 S387 49 421 30 S475 42 503 17 S541 23 560 6" fill="none" stroke="currentColor" strokeWidth="3" vectorEffect="non-scaling-stroke" className="text-primary"/></svg>
              </div><div className="mt-3 flex justify-between px-1 text-[9px] text-base-content/40"><span>MON</span><span>TUE</span><span>WED</span><span>THU</span><span>FRI</span><span>SAT</span><span>SUN</span></div><p className="mt-3 text-center text-[10px] text-base-content/45">Illustrative dashboard preview</p></div>
            </div>
            <div className="absolute -left-5 bottom-12 hidden items-center gap-3 rounded-xl border border-base-300 bg-base-100 p-3 shadow-xl sm:flex"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-success/10 text-lg text-success">↗</span><span><span className="block text-[10px] text-base-content/50">Publisher earnings</span><span className="block text-sm font-semibold">Clear performance</span></span></div>
            <div className="absolute -right-4 top-24 hidden rounded-xl border border-base-300 bg-base-100 px-4 py-3 shadow-xl sm:block"><span className="block text-[10px] text-base-content/50">Campaigns</span><span className="mt-1 block text-sm font-semibold">One simple view</span></div>
          </div>
        </div>
      </section>

      <section id="platform" className="border-y border-base-300 bg-base-200/60"><div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 sm:py-20 lg:px-10"><div className="max-w-2xl"><p className="text-xs font-semibold uppercase tracking-[.2em] text-primary">Everything in sync</p><h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">Run your ad business with less guesswork.</h2><p className="mt-4 text-base leading-7 text-base-content/60">The tools to launch, manage, and understand campaigns—designed to work together from day one.</p></div><div className="mt-10 grid gap-4 md:grid-cols-3">
        {[{ icon: "◈", title: "Campaign control", text: "Set up campaigns, manage creative, and keep budgets and delivery in view." }, { icon: "▤", title: "Publisher inventory", text: "Register sites and ad placements, then follow approval and earnings status." }, { icon: "⌁", title: "Useful performance", text: "See impressions, clicks, and campaign trends in a dashboard built for action." }].map(item => <article key={item.title} className="landing-card rounded-2xl border border-base-300 bg-base-100 p-6 sm:p-7"><span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 font-display text-xl text-primary">{item.icon}</span><h3 className="mt-5 font-display text-lg font-semibold">{item.title}</h3><p className="mt-2 text-sm leading-6 text-base-content/60">{item.text}</p></article>)}
      </div></div></section>

      <section id="how-it-works" className="mx-auto max-w-7xl px-5 py-16 sm:px-8 sm:py-20 lg:px-10"><div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr] lg:items-center"><div><p className="text-xs font-semibold uppercase tracking-[.2em] text-primary">A straightforward start</p><h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">From sign up to first results.</h2><p className="mt-4 max-w-md text-base leading-7 text-base-content/60">Get your workspace ready, take the next step, and see what’s working as activity comes in.</p><Link to="/signup" className="btn btn-primary mt-7">Create your workspace <Arrow /></Link></div><div className="grid gap-3 sm:grid-cols-3">{[{ n: "01", title: "Choose your path", text: "Join as an advertiser or publisher." }, { n: "02", title: "Set up", text: "Create campaigns or register your inventory." }, { n: "03", title: "Grow with insight", text: "Track activity and keep improving." }].map(step => <div key={step.n} className="landing-card rounded-2xl border border-base-300 p-5"><span className="font-mono text-xs font-semibold text-primary">{step.n}</span><h3 className="mt-7 font-display font-semibold">{step.title}</h3><p className="mt-2 text-sm leading-6 text-base-content/60">{step.text}</p></div>)}</div></div></section>

      <section id="for-you" className="mx-5 mb-16 overflow-hidden rounded-3xl bg-neutral text-neutral-content sm:mx-8 sm:mb-20 lg:mx-auto lg:max-w-7xl"><div className="grid lg:grid-cols-2"><div className="p-7 sm:p-10 lg:p-12"><p className="text-xs font-semibold uppercase tracking-[.2em] text-primary">For advertisers</p><h2 className="mt-3 font-display text-3xl font-semibold">Put your next campaign in motion.</h2><p className="mt-3 max-w-md text-sm leading-6 text-neutral-content/65">Organize creative, manage campaign budgets, and follow performance from your advertiser workspace.</p><Link to="/signup" className="btn btn-primary mt-6">Advertise with GetANS <Arrow /></Link></div><div className="border-t border-neutral-content/10 p-7 sm:p-10 lg:border-l lg:border-t-0 lg:p-12"><p className="text-xs font-semibold uppercase tracking-[.2em] text-secondary">For publishers</p><h2 className="mt-3 font-display text-3xl font-semibold">Make more of your audience.</h2><p className="mt-3 max-w-md text-sm leading-6 text-neutral-content/65">Register your site and ad slots, get your inventory reviewed, and keep earnings in view.</p><Link to="/signup" className="btn btn-outline mt-6 border-neutral-content/30 text-neutral-content hover:bg-neutral-content hover:text-neutral">Publish with GetANS <Arrow /></Link></div></div></section>
    </main>
    <footer className="mx-auto flex max-w-7xl flex-col gap-3 px-5 pb-8 text-xs text-base-content/45 sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-10"><Link to="/" className="font-display text-sm font-bold tracking-tight text-base-content/70">GetANS</Link><p>Advertising and publisher tools, together.</p><div className="flex gap-4"><Link to="/login" className="hover:text-base-content">Sign in</Link><Link to="/signup" className="hover:text-base-content">Create account</Link></div></footer>
  </div>;
}
