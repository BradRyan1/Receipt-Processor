# AWS Setup Guide for Receipt Processor

## Quick Setup Steps

### 1. Install AWS CLI
```bash
# Windows (using pip)
pip install awscli

# Or download from AWS website
# https://aws.amazon.com/cli/
```

### 2. Configure AWS Credentials
```bash
aws configure
```

You'll be prompted for:
- **AWS Access Key ID**: Your access key from AWS IAM
- **AWS Secret Access Key**: Your secret key from AWS IAM
- **Default region name**: Use `us-east-1` (or your preferred region)
- **Default output format**: Use `json`

### 3. Create IAM User (if needed)

If you don't have an IAM user with the right permissions:

1. Go to AWS Console → IAM
2. Create a new user or use existing user
3. Attach the following policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "textract:DetectDocumentText",
                "comprehend:DetectEntities",
                "comprehend:DetectKeyPhrases"
            ],
            "Resource": "*"
        }
    ]
}
```

### 4. Generate Access Keys

1. Go to IAM → Users → Your User
2. Security credentials tab
3. Create access key
4. Save the Access Key ID and Secret Access Key

### 5. Test Configuration

```bash
# Test AWS CLI access
aws sts get-caller-identity

# Test Textract access (optional)
aws textract help

# Test Comprehend access (optional)
aws comprehend help
```

## Troubleshooting

### "Unable to locate credentials"
- Run `aws configure` again
- Check that credentials are in `~/.aws/credentials` (Linux/Mac) or `%UserProfile%\.aws\credentials` (Windows)

### "Access Denied" errors
- Verify your IAM user has the required permissions
- Check that you're using the correct region
- Ensure your access keys are active

### Region Issues
- Make sure Textract and Comprehend are available in your region
- Recommended regions: `us-east-1`, `us-west-2`, `eu-west-1`

## Security Best Practices

1. **Use IAM roles** instead of access keys when possible
2. **Rotate access keys** regularly
3. **Use least privilege** - only grant necessary permissions
4. **Monitor usage** through AWS CloudTrail
5. **Never commit credentials** to version control

## Cost Optimization

- **Textract**: ~$1.50 per 1,000 pages
- **Comprehend**: ~$0.0001 per unit (100 characters)
- Monitor usage in AWS Cost Explorer
- Set up billing alerts 