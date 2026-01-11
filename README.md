# product_flow_agent

### About

This agent can help you understand the implementation of current product
It is not going to suggest anything new

### Decision making metrics

one my agent recieve the new feature,
I am expected to kind of suggest similar features

1. I should know for whom the feature is. whats the role of user
2. I should know the scale of changes expected to implement the features. (new feature, UI improvement, UX improvement etc)
3. Flow similarity scores

Output should give a list of possible similar options, along with the similarity scores
This score will be based on the above points. some maths on all the above points

all screens will be in 1 json
all flows would be in 1 json
all interactions would be in 1 json

I can have different nodes,
1st would be to query what screens will be involved
2nd, based on these screens, what could be the flows. suggest 2-3 flows with each with some confidence value
With each flow, tell us the interactions that is there
3rd, from the interactions repo, what are the other options that could have been used

###### inputs:

feature: str = ''
temperature: float = 0

###### output:

```json
{
    feature:
    user_type:
    feature_cat:
    flows: [
        {
            flow: 'login_clicked -> home page -> trending -> ... -> ticket booked',
            screens: [
                {
                    name: '',
                    sequence_num: '',
                    description: '',
                    use: ''
                },
                {}, {}, ...
            ],
            interactions: [
                {
                    name: '',
                    use: '',
                    description: '',

                },
                {}, {}, ...
            ],
        },
        {}, {}, ...
    ]
}
```

### Pipeline

Run the orchestrator with a transcript string:

```bash
python -m src.pipeline.run --app-name "Zapmail" --transcript "Users send emails and view inbox."
```

Run the orchestrator with a transcript file:

```bash
python -m src.pipeline.run --app-name "Zapmail" --transcript-file data/raw/transcript.txt
```

Save the pipeline context to a JSON file:

```bash
python -m src.pipeline.run --input-json data/inputs.json --output data/product_context.json
```

Build a repository context:

```bash
python -m src.pipeline.run --pipeline-type repository --app-name "Zapmail" --transcript "Users send emails and view inbox." --output data/repository_context.json
```

Query the repository:

```bash
python -m src.pipeline.run --pipeline-type query --query "send emails" --repo-context data/repository_context.json
```
