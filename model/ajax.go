package model

import (
	"encoding/json"
	"net/http"
)

type Const struct {
	Success string `json:"success" bson:"success" validate:"required"`
	Error   string `json:"error" bson:"error" validate:"required"`
	Info    string `json:"info" bson:"info" validate:"required"`
	Warning string `json:"warning" bson:"warning" validate:"required"`
}

var Status = Const{
	Success: "success",
	Error:   "error",
	Info:    "info",
	Warning: "warning",
}

type AjaxResponse struct {
	Success  bool        `json:"success"`
	Status   string      `json:"status" validate:"required"`
	Message  string      `json:"message" validate:"required"`
	Data     interface{} `json:"data"`
	Redirect string      `json:"redirect"`
}

func (r *AjaxResponse) MakeResponse(w http.ResponseWriter) {
	if r.Status == Status.Success {
		r.Success = true
	} else {
		r.Success = false
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(r)
}

func ErrorResponse() AjaxResponse {
	return AjaxResponse{
		Success: false,
		Status:  Status.Error,
		Message: "Error message",
	}
}

func InfoResponse() AjaxResponse {
	return AjaxResponse{
		Success: false,
		Status:  Status.Info,
		Message: "Info message",
	}
}

func SuccessResponse() AjaxResponse {
	return AjaxResponse{
		Success: true,
		Status:  Status.Success,
		Message: "Submitted successfully",
	}
}

func WarningResponse() AjaxResponse {
	return AjaxResponse{
		Success: false,
		Status:  Status.Warning,
		Message: "Warning message",
	}
}
