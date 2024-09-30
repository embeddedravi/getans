package model

import (
	"encoding/json"
	"main/defines"
	"net/http"
)

type AjaxResponse struct {
	Success  bool        `json:"success"`
	Status   string      `json:"status" validate:"required"`
	Message  string      `json:"message" validate:"required"`
	Data     interface{} `json:"data"`
	Redirect string      `json:"redirect"`
	IsModal  bool        `json:"isModal"`
	MdlText  string      `json:"mdlText"`
}

func (r AjaxResponse) MakeResponse(w http.ResponseWriter) {
	if r.Status == defines.StatusSuccess {
		r.Success = true
	} else {
		r.Success = false
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(r)
}

func (r AjaxResponse) SetStatus(status ...string) AjaxResponse {
	if len(status) > 0 {
		r.Status = status[0]
	}
	return r
}

func (r AjaxResponse) SetRedirect(url ...string) AjaxResponse {
	if len(url) > 0 {
		r.Redirect = url[0]
	}
	return r
}

func ErrorResponse(error ...string) AjaxResponse {
	message := "Error message"
	if len(error) > 0 {
		message = error[0]
	}
	return AjaxResponse{
		Success: false,
		Status:  defines.StatusError,
		Message: message,
	}
}

func InfoResponse(info ...string) AjaxResponse {
	message := "Info message"
	if len(info) > 0 {
		message = info[0]
	}
	return AjaxResponse{
		Success: false,
		Status:  defines.StatusInfo,
		Message: message,
	}
}

func SuccessResponse(msg ...string) AjaxResponse {
	message := "Submitted successfully"
	if len(msg) > 0 {
		message = msg[0]
	}
	return AjaxResponse{
		Success: true,
		Status:  defines.StatusSuccess,
		Message: message,
	}
}
func WarningResponse(warn ...string) AjaxResponse {
	message := "Warning message"
	if len(warn) > 0 {
		message = warn[0]
	}
	return AjaxResponse{
		Success: false,
		Status:  defines.StatusWarning,
		Message: message,
	}
}

type MdlModel struct {
	MdlTitle      string
	MdlContent    string
	UpdateBtnName string

	NeedCloseBtn  bool
	NeedUpdateBtn bool
}
