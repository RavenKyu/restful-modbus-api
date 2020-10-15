# restful-modbus-api (Restful MODBUS API)

## Template File

```bahs
$ restful-modubs-api -t sample_template.yml
```

```yaml
---
test:
    seconds: 3
    code: |
        def main():
            a = run('read_holding_register --count 4 --ip localhost')
            b = run('read_holding_register --address 40010 --count 2 --ip localhost')
            return a+b
    template:
        - name: temperature1
          note: temperature
          type: B32_FLOAT
        - name: temperature2
    	  note: temperature
          type: B32_FLOAT
```
