package tmpl

import (
	"html/template"
	"net/http"
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

func (p Page) MakePage(w http.ResponseWriter, r *http.Request, tmpl *template.Template) {

	err := tmpl.Execute(w, p)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
}
