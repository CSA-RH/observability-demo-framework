package main

import (  
  "fmt"
  "net/http"
  "time"
//  "os"
  "flag"
) 

type (
  Client struct {
   host       string
   httpClient *http.Client
  }
 )

func NewClient(host string, timeout time.Duration) *Client {
  client := &http.Client{
    Timeout: timeout,     
  }
  return &Client{
    host:       host,
    httpClient: client, 
  }
}

func main() {  
  //client := NewClient("http://127.0.0.1:8080", time.Second * 10);

  flag.Parse()

  if len(flag.Args()) == 0 {
    fmt.Println("Argument not valid")
    return
  }
  switch command := flag.Args()[0]; command {
  case "set":
    fmt.Println("--> Adding metric")
    if len(flag.Args()) != 3 {
      fmt.Println("    Error arguments: Usage promcli add <metric-name> <metric-value>")
      return
    }
    metricName := flag.Args()[1]
    metricValue:= flag.Args()[2]
    fmt.Printf("    Setting metric %s with value %s\n", metricName, metricValue)  
  case "remove":
    fmt.Println("--> Removing metric")
    if len(flag.Args()) != 2 {
      fmt.Println("    Error arguments: Usage promcli remove <metric-name>")
      return
    }
    metricName := flag.Args()[1]
    fmt.Printf("    Deleting metric %s\n", metricName)  
  case "list":
    fmt.Println("--> Listing metrics")
    if len(flag.Args()) != 2 {
      fmt.Println("    Error arguments: Usage promcli remove <metric-name>")
      return
    }
    fmt.Printf("    Listing metrics\n")  
  case "get":
    fmt.Println("--> Getting metric")
    if len(flag.Args()) != 2 {
      fmt.Println("    Error arguments: Usage promcli get <metric-name>")
      return
    }
    metricName := flag.Args()[1]
    fmt.Printf("    Getting metric %s\n", metricName)  
  default:
    fmt.Printf("%s: Command not recognized.\n", command)
  }
}
