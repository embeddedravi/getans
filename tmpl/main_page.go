package tmpl

import (
	"html/template"
	"net/http"
	"os"
)

type BreadCrumbs struct {
	URL  string
	Name string
}
type Page struct {
	Body        template.HTML `required:"true"`
	Title       string        `required:"true"`
	Links       string        `required:"true"`
	JsLinks     string        `required:"true"`
	LogoSVG     string        `required:"true"`
	Breadcrumbs []BreadCrumbs `required:"true"`
}

var SigninPage, SignupPage, IndexPage *template.Template

func init() {
	cwd, err := os.Getwd()
	if err != nil {
		panic(err)
	}
	Path := cwd + "/tmpl/layout/"

	SigninPage = template.Must(template.New("base.html").ParseFiles(Path+"base.html", Path+"common.html", Path+"content/signin.html"))
	SignupPage = template.Must(template.New("base.html").ParseFiles(Path+"base.html", Path+"common.html", Path+"content/signup.html"))
	IndexPage = template.Must(template.New("base.html").ParseFiles(Path+"base.html", Path+"common.html", Path+"content.html"))

}

func (p Page) MakePage(w http.ResponseWriter, r *http.Request, tmpl *template.Template) {

	err := tmpl.Execute(w, p)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
}
