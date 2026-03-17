# ListConversationsV2 API Documentation

## Overview

The `ListConversationsV2` gRPC method retrieves a filtered, paginated list of conversations from the Conversations service. It supports flexible field selection, complex boolean filter trees, multi-field ordering, and two pagination strategies.

**Proto package:** `github.com/uniphore/protos-go/uniphore/conversations/v1`
**gRPC service:** `ConversationsService`
**Methods:**
- `ListConversationsV2` — offset/token-based pagination
- `ListConversationsV2Cursor` — cursor-based pagination using last seen conversation ID (requires LaunchDarkly feature flag `IsEnableUsingLastSeenId`)

---

## Quick Start (Go)

```go
import (
    v1pb "github.com/uniphore/protos-go/uniphore/conversations/v1"
    "google.golang.org/grpc"
)

conn, err := grpc.Dial("conversations-service:50051", grpc.WithInsecure())
client := v1pb.NewConversationsServiceClient(conn)

resp, err := client.ListConversationsV2(ctx, &v1pb.ListConversationsRequestV2{
    TenantId:    "your-tenant-id",
    Environment: "prod",
    GroupFilter: &v1pb.ListConversationsRequestV2_GroupFilter{
        Left: &v1pb.ListConversationsRequestV2_GroupFilter_LeftFilter{
            Filter: &v1pb.ListConversationsRequestV2_Filter{
                Field:    v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_AGENT_ID,
                Operator: v1pb.ListConversationsRequestV2_CONVERSATION_FILTER_OPERATOR_EQUAL,
                Value:    &v1pb.ListConversationsRequestV2_Filter_StringValue{StringValue: "agent-123"},
            },
        },
    },
    Fields: []v1pb.ListConversationsRequestV2_Field{
        v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_CONVERSATION_ID,
        v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_START_TIMESTAMP,
        v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_AGENT_ID,
    },
    PageSize: 50,
})
```

---

## Request: `ListConversationsRequestV2`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tenant_id` | `string` | **Yes** | Tenant identifier. Must match JWT claim if token is present. |
| `environment` | `string` | **Yes** | e.g. `"prod"`, `"staging"` |
| `group_filter` | `GroupFilter` | **Yes** | Root of the filter tree (see [Filters](#filters)) |
| `fields` | `[]Field` | **Yes** | Fields to return in results (see [Available Fields](#available-fields)) |
| `page_size` | `int32` | No | Number of results per page. Default: `10`. Max: `500`. |
| `page_token` | `string` | No | Pagination token from previous response's `next_page_token`. |
| `order_by` | `[]OrderBy` | No | Sort order. Always includes `conversation_id` as a tiebreaker. |

---

## Response: `ListConversationsResponseV2`

| Field | Type | Description |
|-------|------|-------------|
| `conversations` | `[]Conversation` | List of matching conversations |
| `next_page_token` | `string` | Token for the next page. Empty when no more results. |
| `total_count` | `uint64` | Total number of conversations matching the filter |

---

## Filters

Filters use a binary tree (`GroupFilter`) where each node is either a leaf `Filter` or a combination of two sub-filters joined by `AND` / `OR`.

### GroupFilter

```proto
message GroupFilter {
    oneof left  { Filter left_filter  = 1; GroupFilter left_group  = 2; }
    oneof right { Filter right_filter = 3; GroupFilter right_group = 4; }
    GroupOperator operator = 5;  // AND | OR
}
```

The `right` side is optional. If only `left` is set, the group acts as a pass-through for a single filter.

### Filter

```proto
message Filter {
    Field    field    = 1;
    Operator operator = 2;
    oneof value {
        string         string_value  = 3;
        StringValues   string_values = 4;
        double         number_value  = 5;
    }
}
```

### Filter Operators

| Operator | Use Case | Value Type |
|----------|----------|------------|
| `CONVERSATION_FILTER_OPERATOR_EQUAL` | Exact match (scalar fields only) | `string_value` or `number_value` |
| `CONVERSATION_FILTER_OPERATOR_NOT_EQUAL` | Inequality | `string_value` or `number_value` |
| `CONVERSATION_FILTER_OPERATOR_CONTAINS` | String contains substring, or array contains element | `string_value` |
| `CONVERSATION_FILTER_OPERATOR_CONTAINS_ANY` | Array contains any of the given values | `string_values` |
| `CONVERSATION_FILTER_OPERATOR_CONTAINS_ALL` | Array contains all of the given values | `string_values` |
| `CONVERSATION_FILTER_OPERATOR_NOT_CONTAINS` | String/array does not contain | `string_value` |
| `CONVERSATION_FILTER_OPERATOR_NOT_CONTAINS_ANY` | Array does not contain any | `string_values` |
| `CONVERSATION_FILTER_OPERATOR_NOT_CONTAINS_ALL` | Array does not contain all | `string_values` |
| `CONVERSATION_FILTER_OPERATOR_GREATER_THAN` | Numeric / timestamp `>` | `number_value` |
| `CONVERSATION_FILTER_OPERATOR_GREATER_THAN_OR_EQUAL` | Numeric / timestamp `>=` | `number_value` |
| `CONVERSATION_FILTER_OPERATOR_LESS_THAN` | Numeric / timestamp `<` | `number_value` |
| `CONVERSATION_FILTER_OPERATOR_LESS_THAN_OR_EQUAL` | Numeric / timestamp `<=` | `number_value` |
| `CONVERSATION_FILTER_OPERATOR_IN` | Value is one of a list | `string_values` |

> **Important:** Array fields (alerts, annotations, policies, participants, etc.) require `CONTAINS` / `CONTAINS_ANY` operators — using `EQUAL` on an array field returns an error.

### Filter Examples

**Single filter (exact match):**
```go
GroupFilter: &v1pb.ListConversationsRequestV2_GroupFilter{
    Left: &v1pb.ListConversationsRequestV2_GroupFilter_LeftFilter{
        Filter: &v1pb.ListConversationsRequestV2_Filter{
            Field:    v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_CONVERSATION_ID,
            Operator: v1pb.ListConversationsRequestV2_CONVERSATION_FILTER_OPERATOR_EQUAL,
            Value:    &v1pb.ListConversationsRequestV2_Filter_StringValue{StringValue: "conv-abc-123"},
        },
    },
},
```

**AND combination (agent + time range):**
```go
GroupFilter: &v1pb.ListConversationsRequestV2_GroupFilter{
    Left: &v1pb.ListConversationsRequestV2_GroupFilter_LeftFilter{
        Filter: &v1pb.ListConversationsRequestV2_Filter{
            Field:    v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_AGENT_ID,
            Operator: v1pb.ListConversationsRequestV2_CONVERSATION_FILTER_OPERATOR_EQUAL,
            Value:    &v1pb.ListConversationsRequestV2_Filter_StringValue{StringValue: "agent-456"},
        },
    },
    Right: &v1pb.ListConversationsRequestV2_GroupFilter_RightFilter{
        Filter: &v1pb.ListConversationsRequestV2_Filter{
            Field:    v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_START_TIMESTAMP,
            Operator: v1pb.ListConversationsRequestV2_CONVERSATION_FILTER_OPERATOR_GREATER_THAN_OR_EQUAL,
            Value:    &v1pb.ListConversationsRequestV2_Filter_NumberValue{NumberValue: 1700000000},
        },
    },
    Operator: v1pb.ListConversationsRequestV2_GROUP_OPERATOR_AND,
},
```

**IN filter (multiple values):**
```go
Filter: &v1pb.ListConversationsRequestV2_Filter{
    Field:    v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_CONVERSATION_TYPE,
    Operator: v1pb.ListConversationsRequestV2_CONVERSATION_FILTER_OPERATOR_IN,
    Value: &v1pb.ListConversationsRequestV2_Filter_StringValues{
        StringValues: &v1pb.ListConversationsRequestV2_Filter_StringValuesWrapper{
            Values: []string{"VOICE", "CHAT"},
        },
    },
},
```

**Array field filter (conversations with a specific policy):**
```go
Filter: &v1pb.ListConversationsRequestV2_Filter{
    Field:    v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_POLICY_ID,
    Operator: v1pb.ListConversationsRequestV2_CONVERSATION_FILTER_OPERATOR_CONTAINS,
    Value:    &v1pb.ListConversationsRequestV2_Filter_StringValue{StringValue: "policy-xyz"},
},
```

---

## Ordering

```go
OrderBy: []*v1pb.ListConversationsRequestV2_OrderBy{
    {
        Field:     v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_START_TIMESTAMP,
        Direction: v1pb.ListConversationsRequestV2_CONVERSATION_ORDER_DIRECTION_DESC,
    },
},
```

| Direction | Constant |
|-----------|----------|
| Ascending | `CONVERSATION_ORDER_DIRECTION_ASC` |
| Descending | `CONVERSATION_ORDER_DIRECTION_DESC` |

`conversation_id` is always appended as a tiebreaker to ensure deterministic ordering.

---

## Pagination

### Offset-Based (default)

Use `ListConversationsV2`. Pass `next_page_token` from the previous response into the next request's `page_token`. An empty `next_page_token` in the response means there are no more pages.

```go
var pageToken string
for {
    resp, err := client.ListConversationsV2(ctx, &v1pb.ListConversationsRequestV2{
        // ... other fields ...
        PageSize:  100,
        PageToken: pageToken,
    })
    // process resp.Conversations ...
    if resp.NextPageToken == "" {
        break
    }
    pageToken = resp.NextPageToken
}
```

### Cursor-Based (`ListConversationsV2Cursor`)

Enabled per tenant via LaunchDarkly flag `IsEnableUsingLastSeenId`. Uses the `conversation_id` of the last seen conversation as the cursor. Pass `"__first__"` (or empty string) for the first page.

```go
resp, err := client.ListConversationsV2Cursor(ctx, &v1pb.ListConversationsRequestV2{
    // ... other fields ...
    PageSize:  100,
    PageToken: "", // empty = first page
})
// Next page:
resp2, err := client.ListConversationsV2Cursor(ctx, &v1pb.ListConversationsRequestV2{
    // ... other fields ...
    PageToken: resp.NextPageToken, // conversation_id of last record
})
```

---

## Available Fields

Pass these in the `fields` slice to select what data is returned. The same field constants are used in `Filter.Field` and `OrderBy.Field`.

### Core Conversation Fields

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_CONVERSATION_ID` | Internal conversation UUID |
| `CONVERSATION_FIELD_EXTERNAL_CONVERSATION_ID` | External system conversation ID |
| `CONVERSATION_FIELD_START_TIMESTAMP` | Conversation start time (nanosecond epoch) |
| `CONVERSATION_FIELD_END_TIMESTAMP` | Conversation end time (nanosecond epoch); may be zero for live conversations |
| `CONVERSATION_FIELD_DURATION` | Duration in seconds (computed; uses `now()` if conversation is still live) |
| `CONVERSATION_FIELD_AGENT_ID` | Agent identifier |
| `CONVERSATION_FIELD_CONVERSATION_TYPE` | e.g. `VOICE`, `CHAT` |
| `CONVERSATION_FIELD_CONVERSATION_PROVIDER` | Provider of the conversation |
| `CONVERSATION_FIELD_CONVERSATION_BUSINESS_PROCESS_ID` | Business process identifier |
| `CONVERSATION_FIELD_CONVERSATION_EXPERIENCE_ID` | Experience identifier |
| `CONVERSATION_FIELD_CONVERSATION_LIVE` | Boolean — is conversation live |
| `CONVERSATION_FIELD_CONVERSATION_TEST` | Boolean — is test conversation |
| `CONVERSATION_FIELD_LANGUAGE` | Language code |
| `CONVERSATION_FIELD_PRODUCT_TYPE` | Product type |
| `CONVERSATION_FIELD_TARGET_PRODUCTS` | Target product list |
| `CONVERSATION_FIELD_DIRECTION` | Call direction (inbound/outbound) |
| `CONVERSATION_FIELD_ORG_HIERARCHY_ID` | Org hierarchy identifier |
| `CONVERSATION_FIELD_APP_METADATA` | Application metadata (JSON) |
| `CONVERSATION_FIELD_HOLD_TIME` | Total hold time |
| `CONVERSATION_FIELD_LINKED_CONVERSATION_ID` | Linked conversation ID |
| `CONVERSATION_FIELD_SCREEN_RECORDING_STATUS` | Screen recording status |

### State Fields

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_STATE_STATE` | Array of state values |
| `CONVERSATION_FIELD_STATE_TIMESTAMP` | Array of state timestamps |
| `CONVERSATION_FIELD_STATE_LAST_STATE` | Most recent state value |
| `CONVERSATION_FIELD_STATE_V2_STATE` | V2 state array |
| `CONVERSATION_FIELD_STATE_V2_TIMESTAMP` | V2 state timestamp array |
| `CONVERSATION_FIELD_STATE_V2_PRODUCT_TYPE` | V2 state product type array |
| `CONVERSATION_FIELD_U_ANALYZE_STATE_LATEST` | Latest U-Analyze state |
| `CONVERSATION_FIELD_U_ASSIST_STATE_LATEST` | Latest U-Assist state |
| `CONVERSATION_FIELD_U_CAPTURE_STATE_LATEST` | Latest U-Capture state |
| `CONVERSATION_FIELD_U_SELF_SERVE_STATE_LATEST` | Latest U-Self-Serve state |

### Alert Fields (Array)

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_ALERT_ID` | Alert IDs |
| `CONVERSATION_FIELD_ALERT_TIMESTAMP` | Alert timestamps |
| `CONVERSATION_FIELD_ALERT_TYPE` | Alert types |
| `CONVERSATION_FIELD_ALERT_MESSAGE` | Alert messages |
| `CONVERSATION_FIELD_ALERT_STATUS` | Alert statuses |
| `CONVERSATION_FIELD_ALERT_PARTICIPANT_ID` | Alert participant IDs |
| `CONVERSATION_FIELD_ALERT_RECIPIENT` | Alert recipients |
| `CONVERSATION_FIELD_ALERT_INSTANCE_ID` | Alert instance IDs |
| `CONVERSATION_FIELD_ALERT_ACK_STATUS` | Alert acknowledgment statuses |
| `CONVERSATION_FIELD_ALERT_GENERATED_TIME` | Alert generated times |
| `CONVERSATION_FIELD_ALERTS_COUNT` | Total number of alerts |
| `CONVERSATION_FIELD_ALERT_TYPE_CRITICAL_COUNT` | Count of `ALERT_TYPE_CRITICAL` alerts |

### Annotation Fields (Array)

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_ANNOTATION_ID` | Annotation IDs |
| `CONVERSATION_FIELD_ANNOTATION_HEADER` | Annotation headers |
| `CONVERSATION_FIELD_ANNOTATION_TEXT` | Annotation text content |
| `CONVERSATION_FIELD_ANNOTATION_OFFSET` | Offset in seconds |
| `CONVERSATION_FIELD_ANNOTATION_TIMESTAMP` | Annotation timestamps |
| `CONVERSATION_FIELD_ANNOTATION_PARTICIPANT_ID` | Annotation participant IDs |
| `CONVERSATION_FIELD_ANNOTATION_PRODUCT_TYPE` | Annotation product types |
| `CONVERSATION_FIELD_ANNOTATION_TARGET_PRODUCTS` | Annotation target products |

### Policy Fields (Array)

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_POLICY_ID` | Policy IDs (use `CONTAINS`, not `EQUAL`) |
| `CONVERSATION_FIELD_POLICY_ACTION_TYPE` | Policy action types (use `CONTAINS`, not `EQUAL`) |

### Intent Fields (Array)

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_INTENT_LABEL` | Intent labels |
| `CONVERSATION_FIELD_INTENT_TYPE` | Intent types |
| `CONVERSATION_FIELD_INTENT_TIMESTAMP` | Intent timestamps |

### Participant Fields (Array)

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_PARTICIPANT_ID` | Participant IDs |
| `CONVERSATION_FIELD_PARTICIPANT_TYPE` | Participant types |
| `CONVERSATION_FIELD_PARTICIPANT_ANI` | ANI (caller number) |
| `CONVERSATION_FIELD_PARTICIPANT_DNIS` | DNIS (dialed number) |
| `CONVERSATION_FIELD_PARTICIPANT_CTI_AGENT_ID` | CTI agent ID |
| `CONVERSATION_FIELD_PARTICIPANT_SKILL_ID` | Skill ID |
| `CONVERSATION_FIELD_PARTICIPANT_NAME` | Participant name |

### Session Fields

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_SESSION_ID` | Session ID |
| `CONVERSATION_FIELD_SESSION_START_TIMESTAMP` | Session start time |
| `CONVERSATION_FIELD_SESSION_END_TIMESTAMP` | Session end time |
| `CONVERSATION_FIELD_SESSION_TYPE` | Session type |
| `CONVERSATION_FIELD_SESSION_AGENT_ID` | Session agent ID |

### Voice Emotion Summary Fields

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_VOICE_EMOTION_SUMMARY_PARTICIPANT_TYPE` | Participant types |
| `CONVERSATION_FIELD_VOICE_EMOTION_SUMMARY_VOICE_EMOTION_TYPE` | Emotion types |
| `CONVERSATION_FIELD_VOICE_EMOTION_SUMMARY_EMOTION_DURATION` | Emotion durations |
| `CONVERSATION_FIELD_VOICE_EMOTION_SUMMARY_EMOTION_DURATION_NORM` | Normalised emotion durations |
| `CONVERSATION_FIELD_VOICE_EMOTION_SUMMARY_EMOTION_TYPE_SCORE_MEAN` | Mean emotion type score |
| `CONVERSATION_FIELD_VOICE_EMOTION_SUMMARY_VALENCE_TYPE` | Valence types |
| `CONVERSATION_FIELD_VOICE_EMOTION_SUMMARY_VALENCE_DURATION` | Valence durations |
| `CONVERSATION_FIELD_VOICE_EMOTION_SUMMARY_VALENCE_DURATION_NORM` | Normalised valence durations |
| `CONVERSATION_FIELD_VOICE_EMOTION_SUMMARY_VALENCE_TYPE_SCORE_MEAN` | Mean valence type score |

### Transcript Fields

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_TRANSCRIPT_TIMESTAMP` | Transcript timestamp |
| `CONVERSATION_FIELD_TRANSCRIPT_TURN_ORDER` | Turn order numbers |
| `CONVERSATION_FIELD_TRANSCRIPT_TURN_WORDS` | Turn word text |
| `CONVERSATION_FIELD_TRANSCRIPT_TURN_PARTICIPANT_TYPE` | Turn participant types |

### Slot Fields (Array)

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_SLOT_ID` | Slot IDs |
| `CONVERSATION_FIELD_SLOT_TEXT` | Slot text values |
| `CONVERSATION_FIELD_SLOT_ENTITY_ID` | Slot entity IDs |
| `CONVERSATION_FIELD_SLOT_TURN_ORDERS` | Turn orders for each slot |

### Variable Fields (Array)

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_VARIABLES_ID` | Variable IDs |
| `CONVERSATION_FIELD_VARIABLES_NAME` | Variable names |
| `CONVERSATION_FIELD_VARIABLES_VALUE` | Variable values |

### Fact Fields (Array)

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_FACT_ID` | Fact IDs |
| `CONVERSATION_FIELD_FACT_VERSION` | Fact versions |
| `CONVERSATION_FIELD_FACT_RESULT_EXPLANATION` | Result explanations |
| `CONVERSATION_FIELD_FACT_RESULT_CONFIDENCE` | Result confidence scores |
| `CONVERSATION_FIELD_FACT_RESULT_FACT_ID` | Result fact IDs |
| `CONVERSATION_FIELD_FACT_RESULT_TURN_START_OFFSET` | Turn start offsets |
| `CONVERSATION_FIELD_FACT_RESULT_BOOLEAN_VALUE` | Boolean result values |
| `CONVERSATION_FIELD_FACT_RESULT_STRING_VALUE` | String result values |
| `CONVERSATION_FIELD_FACT_RESULT_LIST_VALUE` | List result values |
| `CONVERSATION_FIELD_FACT_RESULT_NUMERIC_VALUE` | Numeric result values |
| `CONVERSATION_FIELD_FACT_RESULT_NUMERIC_UNITS` | Numeric result units |
| `CONVERSATION_FIELD_FACT_RESULT_BOOLEAN_VALUE_FILTER` | Boolean value filter (per fact ID) |
| `CONVERSATION_FIELD_FACT_RESULT_STRING_VALUE_FILTER` | String value filter (per fact ID) |
| `CONVERSATION_FIELD_FACT_RESULT_LIST_VALUE_FILTER` | List value filter (per fact ID) |
| `CONVERSATION_FIELD_FACT_SEMANTIC_RESULT_FACT_ID` | Semantic fact IDs |
| `CONVERSATION_FIELD_FACT_SEMANTIC_RESULT_FACT_VALUE` | Semantic fact values |
| `CONVERSATION_FIELD_FACT_SEMANTIC_RESULT_KEYPHRASES` | Semantic keyphrases |
| `CONVERSATION_FIELD_FACT_SEMANTIC_RESULT_KEYPHRASE_TURNS` | Keyphrase turns |
| `CONVERSATION_FIELD_FACT_SEMANTIC_RESULT_KEYPHRASE_CONFIDENCES` | Keyphrase confidences |
| `CONVERSATION_FIELD_FACT_SEMANTIC_RESULT_KEYPHRASE_TURNOFFSET` | Keyphrase turn offsets |
| `CONVERSATION_FIELD_FACT_SEMANTIC_RESULT_KEYPHRASE_TURNID` | Keyphrase turn IDs |

### Score Card Fields (Array)

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_SCORE_CARD_ID` | Scorecard IDs |
| `CONVERSATION_FIELD_SCORE_CARD_SCORE` | Scores |
| `CONVERSATION_FIELD_SCORE_CARD_TIMESTAMP` | Scorecard timestamps |
| `CONVERSATION_FIELD_SCORE_CARD_PASS_SCORE` | Pass/fail flags |
| `CONVERSATION_FIELD_SCORE_CARD_VERSION` | Scorecard versions |
| `CONVERSATION_FIELD_SCORE_CARD_EVALUATION_STATE` | Evaluation states |
| `CONVERSATION_FIELD_SCORE_CARD_ASSESSMENT_ID` | Assessment IDs |
| `CONVERSATION_FIELD_SCORE_CARD_EVAL_TYPE` | Evaluation types |
| `CONVERSATION_FIELD_SCORE_CARD_SCORE_FILTER` | Score for a specific scorecard ID (per-ID lookup) |
| `CONVERSATION_FIELD_SCORE_CARD_AUTO_FAIL_FILTER` | Scorecard ID in `EVALUATION_STATE_AUTO_FAIL` state |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_ID` | Section IDs |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_PARENT_SECTION_ID` | Parent section IDs |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_SCORE_CARD_ID` | Section's scorecard IDs |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_SCORE` | Section scores |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_TIMESTAMP` | Section timestamps |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_EVALUATION_STATE` | Section evaluation states |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_QUESTION_ID` | Section question IDs |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_QUESTION_SCORE` | Section question scores |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_QUESTION_FACT_ID` | Section question fact IDs |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_QUESTION_TIMESTAMP` | Section question timestamps |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_QUESTION_EVALUATION_STATE` | Section question eval states |
| `CONVERSATION_FIELD_SCORE_CARD_QUESTION_EVALUTION_RESULT` | Section question evaluation results |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_ASSESSMENT_ID` | Section assessment IDs |
| `CONVERSATION_FIELD_SCORE_CARD_SECTION_EVAL_TYPE` | Section evaluation types |

### Manual QM Fields

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_MANUAL_QM_ASSESSMENT_ID` | Assessment ID |
| `CONVERSATION_FIELD_MANUAL_QM_ASSIGNER_ID` | Assigner ID |
| `CONVERSATION_FIELD_MANUAL_QM_EVALUATOR_ID` | Evaluator ID |
| `CONVERSATION_FIELD_MANUAL_QM_EVALUTION_STATUS` | Evaluation status |
| `CONVERSATION_FIELD_MANUAL_QM_EVALUTION_ASSIGNED_AT` | Evaluation assigned timestamp |
| `CONVERSATION_FIELD_MANUAL_QM_EVALUTION_UPDATED_AT` | Evaluation last updated timestamp |

### Fused EQ Score Summary Fields

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_FUSED_EQ_SCORE_SUMMARY_SENTIMENT` | Sentiments |
| `CONVERSATION_FIELD_FUSED_EQ_SCORE_SUMMARY_PARTICIPANT_ID` | Participant IDs |
| `CONVERSATION_FIELD_FUSED_EQ_SCORE_SUMMARY_ENGAGEMENT` | Engagements |

### Sentiment Fields

| Constant | Description |
|----------|-------------|
| `CONVERSATION_FIELD_CALCULATED_SENTIMENT` | Per-participant calculated sentiment (ID, value, type, segment) |
| `CONVERSATION_FIELD_CUSTOMER_SENTIMENT` | Derived customer sentiment (from calculated or fused EQ) |

---

## Authentication

Pass a JWT in the gRPC metadata under the Uniphore authorization header. If the token contains a `tenant` claim, it must match the `tenant_id` in the request.

```go
md := metadata.Pairs("authorization", "Bearer "+jwtToken)
ctx := metadata.NewOutgoingContext(context.Background(), md)
```

---

## Validation Errors

| Condition | gRPC Status |
|-----------|-------------|
| Missing or mismatched `tenant_id` | `INVALID_ARGUMENT` |
| Missing `group_filter` | `INVALID_ARGUMENT` |
| Missing `fields` | `INVALID_ARGUMENT` |
| Missing `environment` | `INVALID_ARGUMENT` |
| `page_size` > 500 | `INVALID_ARGUMENT` |
| `EQUAL` operator on an array field | `INVALID_ARGUMENT` |
| Internal / DB error | `INTERNAL` |

---

## Full Example — Multiple Filters with Pagination

```go
package main

import (
    "context"
    "fmt"
    "log"

    v1pb "github.com/uniphore/protos-go/uniphore/conversations/v1"
    "google.golang.org/grpc"
    "google.golang.org/grpc/metadata"
)

func main() {
    conn, err := grpc.Dial("conversations-service:50051", grpc.WithInsecure())
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()

    client := v1pb.NewConversationsServiceClient(conn)

    md := metadata.Pairs("authorization", "Bearer <your-jwt>")
    ctx := metadata.NewOutgoingContext(context.Background(), md)

    req := &v1pb.ListConversationsRequestV2{
        TenantId:    "tenant-abc",
        Environment: "prod",

        // Filter: agent = "agent-001" AND start_ts >= 1700000000
        GroupFilter: &v1pb.ListConversationsRequestV2_GroupFilter{
            Left: &v1pb.ListConversationsRequestV2_GroupFilter_LeftFilter{
                Filter: &v1pb.ListConversationsRequestV2_Filter{
                    Field:    v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_AGENT_ID,
                    Operator: v1pb.ListConversationsRequestV2_CONVERSATION_FILTER_OPERATOR_EQUAL,
                    Value:    &v1pb.ListConversationsRequestV2_Filter_StringValue{StringValue: "agent-001"},
                },
            },
            Right: &v1pb.ListConversationsRequestV2_GroupFilter_RightFilter{
                Filter: &v1pb.ListConversationsRequestV2_Filter{
                    Field:    v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_START_TIMESTAMP,
                    Operator: v1pb.ListConversationsRequestV2_CONVERSATION_FILTER_OPERATOR_GREATER_THAN_OR_EQUAL,
                    Value:    &v1pb.ListConversationsRequestV2_Filter_NumberValue{NumberValue: 1700000000},
                },
            },
            Operator: v1pb.ListConversationsRequestV2_GROUP_OPERATOR_AND,
        },

        Fields: []v1pb.ListConversationsRequestV2_Field{
            v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_CONVERSATION_ID,
            v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_START_TIMESTAMP,
            v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_END_TIMESTAMP,
            v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_AGENT_ID,
            v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_DURATION,
            v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_ALERTS_COUNT,
        },

        OrderBy: []*v1pb.ListConversationsRequestV2_OrderBy{
            {
                Field:     v1pb.ListConversationsRequestV2_CONVERSATION_FIELD_START_TIMESTAMP,
                Direction: v1pb.ListConversationsRequestV2_CONVERSATION_ORDER_DIRECTION_DESC,
            },
        },

        PageSize: 100,
    }

    var total uint64
    for {
        resp, err := client.ListConversationsV2(ctx, req)
        if err != nil {
            log.Fatal(err)
        }
        total = resp.TotalCount
        for _, conv := range resp.Conversations {
            fmt.Printf("id=%s agent=%s\n", conv.ConversationId, conv.AgentId)
        }
        if resp.NextPageToken == "" {
            break
        }
        req.PageToken = resp.NextPageToken
    }
    fmt.Printf("Total: %d\n", total)
}
```

---

## Key Implementation Files

| File | Purpose |
|------|---------|
| `pkg/server/conversations.go:133` | gRPC handler — `ListConversationsV2` |
| `pkg/server/conversations.go:164` | gRPC handler — `ListConversationsV2Cursor` |
| `pkg/service/conversation_service.go:1383` | Service layer — `ListV2` |
| `pkg/service/conversation_service.go:1413` | Service layer — `ListV2Cursor` |
| `pkg/service/conversation_service.go:1467` | Request validation |
| `pkg/repository/state_index_clickhouse_get_states_v2.go:23` | Field → column mapping |
| `pkg/repository/state_index_clickhouse_get_states_v2.go:258` | Repository `GetStatesV2` (offset) |
| `pkg/repository/state_index_clickhouse_get_states_v2.go:367` | Repository `GetStatesV2Cursor` |
| `pkg/repository/state_index_clickhouse_get_states_v2.go:1043` | Filter operator SQL generation |
